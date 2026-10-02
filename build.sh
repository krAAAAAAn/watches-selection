#!/bin/sh
# Compile Watch Selection pour toutes les plateformes (nécessite Go ≥ 1.22, aucune autre dépendance).
# Résultat : dist/watch-selection-<système>-<processeur>[.exe]
set -e
cd "$(dirname "$0")"
mkdir -p dist
for target in windows/amd64 windows/arm64 darwin/arm64 darwin/amd64 linux/amd64 linux/arm64 linux/arm; do
  os=${target%/*}; arch=${target#*/}
  out="dist/watch-selection-$os-$arch"
  [ "$os" = windows ] && out="$out.exe"
  GOOS=$os GOARCH=$arch GOARM=7 CGO_ENABLED=0 go build -trimpath -ldflags "-s -w" -o "$out" .
  echo "✓ $out"
done
