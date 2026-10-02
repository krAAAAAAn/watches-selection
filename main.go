// Watch Selection — serveur autonome.
//
// Un seul exécutable, sans dépendance : il contient l'application web (dossier app/,
// embarqué à la compilation) et stocke les données dans un dossier à côté de lui.
//
//	watch-selection                       → http://localhost:8080, données dans ./watch-data/
//	watch-selection -port 9000 -data /srv/montres
//
// Points d'API (mêmes que l'ancienne version PHP) :
//
//	GET  /api?a=load     données (watch-data/watches.json, créé depuis les données de départ au 1er lancement)
//	POST /api?a=save     enregistre toutes les données (copie datée de l'ancienne version)
//	POST /api?a=fetch    {id, name, urls[]}     rapatrie une photo distante dans watch-data/img/<id>/
//	POST /api?a=upload   {id, name, dataUrl}    enregistre une photo envoyée (dépôt, détourage)
//
// Pas d'authentification : l'accès depuis l'extérieur passe par un reverse-proxy (Pangolin).
package main

import (
	"bytes"
	"crypto/md5"
	"embed"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"io/fs"
	"log"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"sync"
	"time"
)

//go:embed app
var embedded embed.FS

const (
	keepBackups   = 50
	maxImageBytes = 15 << 20
	maxBodyBytes  = 60 << 20
)

var (
	dataDir     string
	saveMu      sync.Mutex
	unsafeChars = regexp.MustCompile(`[^a-z0-9-]+`)
)

func main() {
	port := flag.Int("port", 8080, "port d'écoute")
	host := flag.String("host", "0.0.0.0", "adresse d'écoute (127.0.0.1 = cette machine seulement)")
	data := flag.String("data", "", "dossier des données (défaut : watch-data/ à côté de l'exécutable)")
	flag.Parse()

	dataDir = *data
	if dataDir == "" {
		exe, err := os.Executable()
		if err != nil {
			log.Fatal(err)
		}
		dataDir = filepath.Join(filepath.Dir(exe), "watch-data")
	}
	for _, d := range []string{dataDir, filepath.Join(dataDir, "backup"), filepath.Join(dataDir, "img")} {
		if err := os.MkdirAll(d, 0o755); err != nil {
			log.Fatalf("Impossible de créer %s : %v", d, err)
		}
	}

	web, _ := fs.Sub(embedded, "app")
	mux := http.NewServeMux()
	mux.HandleFunc("/api", handleAPI)
	mux.Handle("/img/", http.StripPrefix("/img/", http.FileServer(http.Dir(filepath.Join(dataDir, "img")))))
	mux.Handle("/", http.FileServer(http.FS(web)))

	addr := fmt.Sprintf("%s:%d", *host, *port)
	ln, err := net.Listen("tcp", addr)
	if err != nil {
		log.Fatalf("Port %d indisponible : %v (essayer -port 9000)", *port, err)
	}
	log.Printf("Watch Selection — données : %s", dataDir)
	log.Printf("Ouvrir http://localhost:%d (ou http://<adresse-de-cette-machine>:%d depuis le téléphone)", *port, *port)
	log.Fatal(http.Serve(ln, noCache(mux)))
}

// Les données et l'application changent : pas de cache navigateur sur l'API ni sur index.html.
func noCache(h http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/" || r.URL.Path == "/index.html" || r.URL.Path == "/api" {
			w.Header().Set("Cache-Control", "no-store")
		}
		h.ServeHTTP(w, r)
	})
}

func reply(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(code)
	enc := json.NewEncoder(w)
	enc.SetEscapeHTML(false)
	enc.Encode(v)
}

func fail(w http.ResponseWriter, code int, msg string) {
	reply(w, code, map[string]string{"error": msg})
}

func handleAPI(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Cache-Control", "no-store")
	action := r.URL.Query().Get("a")
	if action != "load" && r.Method != http.MethodPost {
		fail(w, http.StatusMethodNotAllowed, "POST attendu")
		return
	}
	r.Body = http.MaxBytesReader(w, r.Body, maxBodyBytes)
	switch action {
	case "load":
		apiLoad(w)
	case "save":
		apiSave(w, r)
	case "fetch":
		apiFetch(w, r)
	case "upload":
		apiUpload(w, r)
	default:
		fail(w, http.StatusNotFound, "Action inconnue")
	}
}

func dataFile() string { return filepath.Join(dataDir, "watches.json") }

func apiLoad(w http.ResponseWriter) {
	b, err := os.ReadFile(dataFile())
	if errors.Is(err, os.ErrNotExist) { // premier lancement : données de départ embarquées
		b, err = embedded.ReadFile("app/seed/watches.json")
		if err == nil {
			err = os.WriteFile(dataFile(), b, 0o644)
		}
	}
	if err != nil {
		fail(w, 500, "Lecture impossible : "+err.Error())
		return
	}
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Write(b)
}

// Enregistre tout le fichier. Chaque version porte un numéro « rev » : une sauvegarde faite
// à partir d'une version périmée (autre appareil resté ouvert) est refusée (409) au lieu
// d'écraser silencieusement les changements faits ailleurs.
func apiSave(w http.ResponseWriter, r *http.Request) {
	raw, err := io.ReadAll(r.Body)
	if err != nil {
		fail(w, 400, "Lecture de la requête impossible")
		return
	}
	var doc map[string]json.RawMessage
	if json.Unmarshal(raw, &doc) != nil || doc["watches"] == nil || doc["categories"] == nil {
		fail(w, 400, "Données invalides : rien enregistré")
		return
	}

	saveMu.Lock()
	defer saveMu.Unlock()
	old, _ := os.ReadFile(dataFile())
	current := revOf(old)
	if base := revOfField(doc["rev"]); old != nil && base != current {
		reply(w, http.StatusConflict, map[string]any{"error": "conflict", "rev": current})
		return
	}
	doc["rev"], _ = json.Marshal(current + 1)
	out, _ := json.MarshalIndent(doc, "", " ")

	if old != nil { // sauvegarde de la version précédente
		name := "watches-" + time.Now().Format("20060102-150405.000") + ".json"
		os.WriteFile(filepath.Join(dataDir, "backup", name), old, 0o644)
		pruneBackups()
	}
	tmp := dataFile() + ".tmp"
	if err := os.WriteFile(tmp, out, 0o644); err != nil {
		fail(w, 500, "Écriture impossible : "+err.Error())
		return
	}
	if err := os.Rename(tmp, dataFile()); err != nil { // écriture atomique
		fail(w, 500, "Écriture impossible : "+err.Error())
		return
	}
	reply(w, 200, map[string]any{"ok": true, "rev": current + 1, "saved": time.Now().Format(time.RFC3339)})
}

func revOf(file []byte) int {
	var d struct {
		Rev int `json:"rev"`
	}
	json.Unmarshal(file, &d)
	return d.Rev
}

func revOfField(raw json.RawMessage) int {
	var n int
	json.Unmarshal(raw, &n)
	return n
}

func pruneBackups() {
	files, _ := filepath.Glob(filepath.Join(dataDir, "backup", "watches-*.json"))
	sort.Strings(files)
	for len(files) > keepBackups {
		os.Remove(files[0])
		files = files[1:]
	}
}

func safe(s string) string {
	s = strings.Trim(unsafeChars.ReplaceAllString(strings.ToLower(s), "-"), "-")
	if len(s) > 60 {
		s = strings.Trim(s[:60], "-")
	}
	if s == "" {
		return "x"
	}
	return s
}

// Reconnaît une image par sa signature (sans dépendance) et renvoie l'extension.
func imageExt(b []byte) string {
	switch {
	case bytes.HasPrefix(b, []byte("\x89PNG\r\n\x1a\n")):
		return "png"
	case bytes.HasPrefix(b, []byte{0xFF, 0xD8, 0xFF}):
		return "jpg"
	case bytes.HasPrefix(b, []byte("GIF8")):
		return "gif"
	case len(b) > 12 && string(b[:4]) == "RIFF" && string(b[8:12]) == "WEBP":
		return "webp"
	case len(b) > 12 && string(b[4:8]) == "ftyp" && (string(b[8:12]) == "avif" || string(b[8:12]) == "avis"):
		return "avif"
	}
	return ""
}

func storeImage(b []byte, id, name string) (string, error) {
	if len(b) > maxImageBytes {
		return "", errors.New("image trop lourde")
	}
	ext := imageExt(b)
	if ext == "" {
		return "", errors.New("ce fichier n'est pas une image reconnue")
	}
	dir := filepath.Join(dataDir, "img", safe(id))
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return "", err
	}
	sum := md5.Sum(b)
	// nom unique : pas de souci de cache quand une photo est remplacée
	file := fmt.Sprintf("%s-%s-%s.%s", safe(name), time.Now().Format("20060102150405"), hex.EncodeToString(sum[:3]), ext)
	if err := os.WriteFile(filepath.Join(dir, file), b, 0o644); err != nil {
		return "", err
	}
	return "img/" + safe(id) + "/" + file, nil
}

var client = &http.Client{Timeout: 25 * time.Second}

func apiFetch(w http.ResponseWriter, r *http.Request) {
	var req struct {
		ID, Name string
		URLs     []string `json:"urls"`
	}
	if json.NewDecoder(r.Body).Decode(&req) != nil {
		fail(w, 400, "Corps JSON invalide")
		return
	}
	var errs []string
	for _, u := range req.URLs {
		if !strings.HasPrefix(u, "http://") && !strings.HasPrefix(u, "https://") {
			errs = append(errs, u+" : adresse refusée")
			continue
		}
		b, err := download(u)
		if err != nil {
			errs = append(errs, u+" : "+err.Error())
			continue
		}
		src, err := storeImage(b, or(req.ID, "divers"), or(req.Name, "photo"))
		if err != nil {
			errs = append(errs, u+" : "+err.Error())
			continue
		}
		reply(w, 200, map[string]string{"src": src, "from": u})
		return
	}
	fail(w, 502, "Aucune source n'a fonctionné — "+strings.Join(errs, " | "))
}

func download(u string) ([]byte, error) {
	req, err := http.NewRequest("GET", u, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36")
	req.Header.Set("Accept", "image/avif,image/webp,image/png,image/jpeg,image/*;q=0.8")
	res, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer res.Body.Close()
	if res.StatusCode >= 400 {
		return nil, fmt.Errorf("HTTP %d", res.StatusCode)
	}
	return io.ReadAll(io.LimitReader(res.Body, maxImageBytes+1))
}

var dataURL = regexp.MustCompile(`^data:image/[a-z+]+;base64,`)

func apiUpload(w http.ResponseWriter, r *http.Request) {
	var req struct{ ID, Name, DataURL string }
	if json.NewDecoder(r.Body).Decode(&req) != nil {
		fail(w, 400, "Corps JSON invalide")
		return
	}
	loc := dataURL.FindStringIndex(req.DataURL)
	if loc == nil {
		fail(w, 400, "Image attendue (data URL)")
		return
	}
	b, err := base64.StdEncoding.DecodeString(req.DataURL[loc[1]:])
	if err != nil {
		fail(w, 400, "Image mal encodée")
		return
	}
	src, err := storeImage(b, or(req.ID, "divers"), or(req.Name, "photo"))
	if err != nil {
		fail(w, 400, err.Error())
		return
	}
	reply(w, 200, map[string]string{"src": src})
}

func or(s, def string) string {
	if s == "" {
		return def
	}
	return s
}
