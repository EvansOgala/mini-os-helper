# mini-os-helper-git AUR Staging Folder

This folder mirrors the package files intended for the AUR repository.

Files to publish:

- `PKGBUILD`
- `.SRCINFO`

Typical workflow:

```bash
git clone ssh://aur@aur.archlinux.org/mini-os-helper-git.git
cd mini-os-helper-git
cp /path/to/your/source/repo/aur/mini-os-helper-git/PKGBUILD .
cp /path/to/your/source/repo/aur/mini-os-helper-git/.SRCINFO .
git add PKGBUILD .SRCINFO
git commit -m "Initial import"
git push
```
