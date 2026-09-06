// Command contextpack decide quais arquivos de um projeto cabem na janela de
// contexto de um LLM, dado um orçamento de tokens, priorizando os arquivos
// modificados mais recentemente. A seleção usa o algoritmo clássico da
// mochila 0/1 (0/1 knapsack) para maximizar a prioridade total sem estourar
// o orçamento.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io/fs"
	"math"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

// FileCandidate representa um arquivo elegível para entrar no contexto.
type FileCandidate struct {
	Path         string    `json:"path"`
	Tokens       int       `json:"tokens_estimados"`
	ModTime      time.Time `json:"-"`
	Priority     int       `json:"prioridade"`
	AgeInDaysStr string    `json:"idade"`
}

// defaultExtensions lista as extensões consideradas "código/texto" por padrão.
var defaultExtensions = map[string]bool{
	".go": true, ".py": true, ".js": true, ".ts": true, ".tsx": true, ".jsx": true,
	".java": true, ".rb": true, ".rs": true, ".c": true, ".h": true, ".cpp": true,
	".md": true, ".txt": true, ".json": true, ".yaml": true, ".yml": true,
	".sh": true, ".sql": true,
}

// ignoredDirs nunca são varridos (ruído ou dados gerados, não código-fonte).
var ignoredDirs = map[string]bool{
	".git": true, "node_modules": true, "vendor": true, ".venv": true,
	"__pycache__": true, "dist": true, "build": true,
}

// EstimateTokens aproxima a contagem de tokens de um LLM usando a heurística
// amplamente adotada de ~4 caracteres por token para texto/código em inglês
// (documentada, por exemplo, pela OpenAI). Não é uma contagem exata via BPE
// (isso exigiria as tabelas de merge do tokenizer real, fora do escopo aqui),
// mas é suficiente para decidir orçamento de contexto com boa margem.
func EstimateTokens(content []byte) int {
	if len(content) == 0 {
		return 0
	}
	return int(math.Ceil(float64(len(content)) / 4.0))
}

// PriorityFromAge converte a idade de um arquivo (dias desde a última
// modificação) em uma pontuação de prioridade: quanto mais recente, maior a
// pontuação. Arquivos com mais de 365 dias têm prioridade mínima (1).
func PriorityFromAge(ageInDays int) int {
	score := 365 - ageInDays
	if score < 1 {
		score = 1
	}
	return score
}

// KnapsackResult é o resultado da seleção ótima.
type KnapsackResult struct {
	Selected      []FileCandidate
	Excluded      []FileCandidate
	TotalTokens   int
	TotalPriority int
}

// SolveKnapsack resolve o problema da mochila 0/1: dado um orçamento de
// tokens (capacidade) e uma lista de arquivos (cada um com peso = tokens e
// valor = prioridade), encontra o subconjunto que maximiza a prioridade
// total sem exceder o orçamento. Complexidade O(n*budget) em tempo e memória,
// clássica para instâncias pequenas/médias (repositórios de até dezenas de
// milhares de tokens de orçamento).
func SolveKnapsack(files []FileCandidate, budget int) KnapsackResult {
	n := len(files)
	if budget < 0 {
		budget = 0
	}

	// dp[i][w] = maior prioridade alcançável usando os primeiros i arquivos
	// com capacidade w.
	dp := make([][]int, n+1)
	for i := range dp {
		dp[i] = make([]int, budget+1)
	}

	for i := 1; i <= n; i++ {
		weight := files[i-1].Tokens
		value := files[i-1].Priority
		for w := 0; w <= budget; w++ {
			dp[i][w] = dp[i-1][w]
			if weight <= w {
				withItem := dp[i-1][w-weight] + value
				if withItem > dp[i][w] {
					dp[i][w] = withItem
				}
			}
		}
	}

	// Backtracking para descobrir quais itens foram escolhidos.
	selectedIdx := make(map[int]bool)
	w := budget
	for i := n; i > 0; i-- {
		if dp[i][w] != dp[i-1][w] {
			selectedIdx[i-1] = true
			w -= files[i-1].Tokens
		}
	}

	result := KnapsackResult{}
	for i, f := range files {
		if selectedIdx[i] {
			result.Selected = append(result.Selected, f)
			result.TotalTokens += f.Tokens
			result.TotalPriority += f.Priority
		} else {
			result.Excluded = append(result.Excluded, f)
		}
	}

	// Ordena a saída por prioridade decrescente para leitura mais natural.
	sort.SliceStable(result.Selected, func(a, b int) bool {
		return result.Selected[a].Priority > result.Selected[b].Priority
	})
	sort.SliceStable(result.Excluded, func(a, b int) bool {
		return result.Excluded[a].Priority > result.Excluded[b].Priority
	})

	return result
}

// ScanDirectory percorre root recursivamente e retorna um FileCandidate para
// cada arquivo cuja extensão esteja em extensions, ignorando diretórios
// ruidosos (.git, node_modules, etc). now é injetado para tornar o cálculo de
// idade determinístico em testes.
func ScanDirectory(root string, extensions map[string]bool, now time.Time) ([]FileCandidate, error) {
	var candidates []FileCandidate

	err := filepath.WalkDir(root, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			if ignoredDirs[d.Name()] {
				return filepath.SkipDir
			}
			return nil
		}
		ext := strings.ToLower(filepath.Ext(path))
		if !extensions[ext] {
			return nil
		}
		info, err := d.Info()
		if err != nil {
			return err
		}
		content, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		ageInDays := int(now.Sub(info.ModTime()).Hours() / 24)
		rel, err := filepath.Rel(root, path)
		if err != nil {
			rel = path
		}
		candidates = append(candidates, FileCandidate{
			Path:         rel,
			Tokens:       EstimateTokens(content),
			ModTime:      info.ModTime(),
			Priority:     PriorityFromAge(ageInDays),
			AgeInDaysStr: fmt.Sprintf("%dd", ageInDays),
		})
		return nil
	})
	if err != nil {
		return nil, err
	}
	return candidates, nil
}

func parseExtensions(raw string) map[string]bool {
	if raw == "" {
		return defaultExtensions
	}
	exts := map[string]bool{}
	for _, e := range strings.Split(raw, ",") {
		e = strings.TrimSpace(e)
		if e == "" {
			continue
		}
		if !strings.HasPrefix(e, ".") {
			e = "." + e
		}
		exts[strings.ToLower(e)] = true
	}
	return exts
}

func printReport(res KnapsackResult, budget int) {
	fmt.Printf("Orçamento: %d tokens | Usado: %d tokens (%.1f%%) | Prioridade total: %d\n\n",
		budget, res.TotalTokens, 100*float64(res.TotalTokens)/math.Max(1, float64(budget)), res.TotalPriority)

	fmt.Printf("Incluídos no contexto (%d arquivos):\n", len(res.Selected))
	for _, f := range res.Selected {
		fmt.Printf("  [+] %-50s %6d tokens  (idade %s, prioridade %d)\n", f.Path, f.Tokens, f.AgeInDaysStr, f.Priority)
	}

	fmt.Printf("\nExcluídos por orçamento (%d arquivos):\n", len(res.Excluded))
	for _, f := range res.Excluded {
		fmt.Printf("  [-] %-50s %6d tokens  (idade %s, prioridade %d)\n", f.Path, f.Tokens, f.AgeInDaysStr, f.Priority)
	}
}

func printJSON(res KnapsackResult, budget int) error {
	out := struct {
		Budget        int             `json:"orcamento_tokens"`
		TotalTokens   int             `json:"tokens_usados"`
		TotalPriority int             `json:"prioridade_total"`
		Selected      []FileCandidate `json:"incluidos"`
		Excluded      []FileCandidate `json:"excluidos"`
	}{budget, res.TotalTokens, res.TotalPriority, res.Selected, res.Excluded}
	if out.Selected == nil {
		out.Selected = []FileCandidate{}
	}
	if out.Excluded == nil {
		out.Excluded = []FileCandidate{}
	}
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	return enc.Encode(out)
}

func main() {
	dir := flag.String("dir", ".", "diretório raiz a ser escaneado")
	budget := flag.Int("budget", 8000, "orçamento de tokens da janela de contexto")
	ext := flag.String("ext", "", "lista de extensões separadas por vírgula (ex: go,py,md). Padrão: conjunto comum de código/texto")
	jsonOut := flag.Bool("json", false, "imprime o resultado em JSON em vez de texto")
	flag.Parse()

	extensions := parseExtensions(*ext)

	candidates, err := ScanDirectory(*dir, extensions, time.Now())
	if err != nil {
		fmt.Fprintf(os.Stderr, "erro ao escanear %q: %v\n", *dir, err)
		os.Exit(1)
	}
	if len(candidates) == 0 {
		fmt.Fprintf(os.Stderr, "nenhum arquivo elegível encontrado em %q\n", *dir)
		os.Exit(1)
	}

	result := SolveKnapsack(candidates, *budget)

	if *jsonOut {
		if err := printJSON(result, *budget); err != nil {
			fmt.Fprintf(os.Stderr, "erro ao gerar JSON: %v\n", err)
			os.Exit(1)
		}
		return
	}
	printReport(result, *budget)
}
