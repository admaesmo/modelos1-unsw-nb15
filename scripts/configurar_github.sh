#!/usr/bin/env bash
# Configura el repositorio del equipo en GitHub (se ejecuta UNA sola vez, lo hace el dueño del repo).
#
# Requisitos:
#   - GitHub CLI instalado y autenticado:  sudo apt install gh  &&  gh auth login
#   - Repo local con el commit inicial en main y el remoto origin apuntando a GitHub.
#
# Uso (desde la raíz del repositorio):
#   bash scripts/configurar_github.sh <usuario_compañero_1> <usuario_compañero_2>
#
# Qué hace:
#   1. Sube main y crea develop y las ramas feature de la fase 1.
#   2. Pone develop como rama por defecto y borra ramas automáticamente tras el merge.
#   3. Protege main y develop: solo aceptan cambios por Pull Request con 1 aprobación.
#   4. Invita a los compañeros como colaboradores con permiso de escritura.

set -euo pipefail

RAMAS_FEATURE=(
  "feature/entorno-y-verificacion"
  "feature/eda-y-limpieza"
  "feature/pipeline-y-modelo"
)

if [[ $# -lt 1 ]]; then
  echo "Uso: bash scripts/configurar_github.sh <usuario_compañero_1> [usuario_compañero_2]"
  exit 1
fi
COLABORADORES=("$@")

command -v gh >/dev/null || { echo "ERROR: instala GitHub CLI (sudo apt install gh) y ejecuta 'gh auth login'."; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "ERROR: ejecuta 'gh auth login' primero."; exit 1; }
git remote get-url origin >/dev/null 2>&1 || { echo "ERROR: falta el remoto: git remote add origin git@github.com:<usuario>/<repo>.git"; exit 1; }
[[ "$(git branch --show-current)" == "main" ]] || { echo "ERROR: ejecuta el script desde la rama main."; exit 1; }
[[ -z "$(git status --porcelain --untracked-files=no)" ]] || { echo "ERROR: hay cambios sin commitear en archivos versionados."; exit 1; }

REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
echo "Repositorio: $REPO"

echo -e "\n[1/4] Ramas"
git push -u origin main
git show-ref --verify --quiet refs/heads/develop || git branch develop main
git push -u origin develop
for rama in "${RAMAS_FEATURE[@]}"; do
  git show-ref --verify --quiet "refs/heads/$rama" || git branch "$rama" develop
  git push -u origin "$rama"
done

echo -e "\n[2/4] Rama por defecto = develop y borrado automático de ramas fusionadas"
gh api -X PATCH "repos/$REPO" -f default_branch=develop -F delete_branch_on_merge=true >/dev/null

echo -e "\n[3/4] Protección de main y develop"
PROTECCION='{
  "required_status_checks": null,
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}'
for rama in main develop; do
  if echo "$PROTECCION" | gh api -X PUT "repos/$REPO/branches/$rama/protection" --input - >/dev/null 2>/tmp/proteccion_err; then
    echo "  $rama: protegida (solo Pull Request con 1 aprobación)"
  else
    echo "  $rama: NO se pudo proteger: $(cat /tmp/proteccion_err)"
    echo "  Si el repo es privado con cuenta gratuita, GitHub no permite proteger ramas:"
    echo "  hazlo público (Settings → General → Danger Zone → Change visibility) y vuelve a ejecutar."
  fi
done

echo -e "\n[4/4] Colaboradores"
for usuario in "${COLABORADORES[@]}"; do
  gh api -X PUT "repos/$REPO/collaborators/$usuario" -f permission=push >/dev/null \
    && echo "  Invitación enviada a @$usuario (debe aceptarla en https://github.com/$REPO/invitations)"
done

git switch -q develop
echo -e "\nListo. Ramas de trabajo:"
for i in "${!RAMAS_FEATURE[@]}"; do echo "  Integrante $((i + 1)): ${RAMAS_FEATURE[$i]}"; done
echo "Repositorio: https://github.com/$REPO"
