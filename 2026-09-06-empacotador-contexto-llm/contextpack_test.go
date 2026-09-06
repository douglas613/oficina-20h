package main

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestEstimateTokens(t *testing.T) {
	cases := []struct {
		name    string
		content []byte
		want    int
	}{
		{"vazio", []byte(""), 0},
		{"quatro chars", []byte("abcd"), 1},
		{"cinco chars arredonda pra cima", []byte("abcde"), 2},
		{"oito chars", []byte("abcdefgh"), 2},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got := EstimateTokens(c.content)
			if got != c.want {
				t.Errorf("EstimateTokens(%q) = %d, want %d", c.content, got, c.want)
			}
		})
	}
}

func TestPriorityFromAge(t *testing.T) {
	if got := PriorityFromAge(0); got != 365 {
		t.Errorf("arquivo de hoje deveria ter prioridade máxima 365, got %d", got)
	}
	if got := PriorityFromAge(364); got != 1 {
		t.Errorf("arquivo de 364 dias deveria ter prioridade 1, got %d", got)
	}
	if got := PriorityFromAge(1000); got != 1 {
		t.Errorf("prioridade nunca deve ser menor que 1, got %d", got)
	}
}

func TestSolveKnapsack_ClassicCase(t *testing.T) {
	// Instância clássica de mochila 0/1 com solução conhecida:
	// itens (peso, valor): (2,3) (3,4) (4,5) (5,6), capacidade 5
	// solução ótima: itens de peso 2 e 3 -> valor 7, peso 5.
	files := []FileCandidate{
		{Path: "a", Tokens: 2, Priority: 3},
		{Path: "b", Tokens: 3, Priority: 4},
		{Path: "c", Tokens: 4, Priority: 5},
		{Path: "d", Tokens: 5, Priority: 6},
	}
	res := SolveKnapsack(files, 5)
	if res.TotalPriority != 7 {
		t.Fatalf("prioridade total = %d, want 7", res.TotalPriority)
	}
	if res.TotalTokens != 5 {
		t.Fatalf("tokens totais = %d, want 5", res.TotalTokens)
	}
	if len(res.Selected) != 2 {
		t.Fatalf("esperado 2 arquivos selecionados, got %d", len(res.Selected))
	}
}

func TestSolveKnapsack_BudgetZero(t *testing.T) {
	files := []FileCandidate{{Path: "a", Tokens: 1, Priority: 1}}
	res := SolveKnapsack(files, 0)
	if len(res.Selected) != 0 {
		t.Fatalf("orçamento zero não deveria selecionar nada, got %d", len(res.Selected))
	}
	if len(res.Excluded) != 1 {
		t.Fatalf("esperado 1 arquivo excluído, got %d", len(res.Excluded))
	}
}

func TestSolveKnapsack_BudgetCoversEverything(t *testing.T) {
	files := []FileCandidate{
		{Path: "a", Tokens: 10, Priority: 1},
		{Path: "b", Tokens: 20, Priority: 2},
	}
	res := SolveKnapsack(files, 1000)
	if len(res.Selected) != 2 {
		t.Fatalf("orçamento generoso deveria incluir tudo, got %d selecionados", len(res.Selected))
	}
	if len(res.Excluded) != 0 {
		t.Fatalf("esperado 0 excluídos, got %d", len(res.Excluded))
	}
}

func TestSolveKnapsack_NeverExceedsBudget(t *testing.T) {
	files := []FileCandidate{
		{Path: "a", Tokens: 7, Priority: 5},
		{Path: "b", Tokens: 7, Priority: 5},
		{Path: "c", Tokens: 7, Priority: 5},
	}
	res := SolveKnapsack(files, 10)
	if res.TotalTokens > 10 {
		t.Fatalf("tokens usados (%d) excederam o orçamento (10)", res.TotalTokens)
	}
}

func TestScanDirectory(t *testing.T) {
	dir := t.TempDir()

	// Arquivo elegível recente.
	recentPath := filepath.Join(dir, "recente.go")
	if err := os.WriteFile(recentPath, []byte("package main\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	// Arquivo elegível antigo (mtime forçado no passado).
	oldPath := filepath.Join(dir, "antigo.md")
	if err := os.WriteFile(oldPath, []byte("# titulo antigo"), 0o644); err != nil {
		t.Fatal(err)
	}
	oldTime := time.Now().Add(-200 * 24 * time.Hour)
	if err := os.Chtimes(oldPath, oldTime, oldTime); err != nil {
		t.Fatal(err)
	}

	// Extensão não elegível, deve ser ignorada.
	if err := os.WriteFile(filepath.Join(dir, "binario.exe"), []byte{0x00, 0x01}, 0o644); err != nil {
		t.Fatal(err)
	}

	// Diretório ignorado, deve ser pulado por completo.
	ignoredDir := filepath.Join(dir, "node_modules")
	if err := os.MkdirAll(ignoredDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(ignoredDir, "lib.js"), []byte("ignorar isso"), 0o644); err != nil {
		t.Fatal(err)
	}

	candidates, err := ScanDirectory(dir, defaultExtensions, time.Now())
	if err != nil {
		t.Fatalf("ScanDirectory retornou erro: %v", err)
	}

	if len(candidates) != 2 {
		t.Fatalf("esperado 2 candidatos (recente.go, antigo.md), got %d: %+v", len(candidates), candidates)
	}

	var recentCandidate, oldCandidate *FileCandidate
	for i := range candidates {
		switch candidates[i].Path {
		case "recente.go":
			recentCandidate = &candidates[i]
		case "antigo.md":
			oldCandidate = &candidates[i]
		}
	}
	if recentCandidate == nil || oldCandidate == nil {
		t.Fatalf("não encontrou os candidatos esperados: %+v", candidates)
	}
	if recentCandidate.Priority <= oldCandidate.Priority {
		t.Errorf("arquivo recente deveria ter prioridade maior que o antigo: recente=%d antigo=%d",
			recentCandidate.Priority, oldCandidate.Priority)
	}
}

func TestParseExtensions(t *testing.T) {
	exts := parseExtensions("go, py,.md")
	want := []string{".go", ".py", ".md"}
	for _, w := range want {
		if !exts[w] {
			t.Errorf("esperava extensão %q presente no set: %+v", w, exts)
		}
	}
	if len(exts) != len(want) {
		t.Errorf("esperava exatamente %d extensões, got %d: %+v", len(want), len(exts), exts)
	}

	def := parseExtensions("")
	if len(def) != len(defaultExtensions) {
		t.Errorf("string vazia deveria retornar defaultExtensions")
	}
}
