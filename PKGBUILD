pkgname=mini-os-helper-git
pkgver=0.r12.gd974efd
pkgrel=1
pkgdesc="GTK4 system helper dashboard with quick actions and notes"
arch=('any')
url="https://github.com/EvansOgala/mini-os-helper"
license=('MIT')
options=('!strip' '!debug')
depends=(
  'python'
  'python-gobject'
  'gtk4'
  'xdg-utils'
  'python-psutil'
)
makedepends=('git')
source=("$pkgname::git+https://github.com/EvansOgala/mini-os-helper.git")
sha256sums=('SKIP')

pkgver() {
  cd "$srcdir/$pkgname"
  printf "0.r%s.g%s" \
    "$(git rev-list --count HEAD)" \
    "$(git rev-parse --short HEAD)"
}

build() {
  cd "$srcdir/$pkgname"
  python3 -m PyInstaller --clean --noconfirm --log-level=ERROR MiniOSHelper.spec
}

package() {
  cd "$srcdir/$pkgname"

  install -d "$pkgdir/usr/lib/mini-os-helper"
  cp -a dist/MiniOSHelper/. "$pkgdir/usr/lib/mini-os-helper/"

  install -Dm755 /dev/stdin "$pkgdir/usr/bin/mini-os-helper" <<'LAUNCHER'
#!/bin/sh
exec /usr/lib/mini-os-helper/MiniOSHelper "$@"
LAUNCHER

  install -Dm644 org.evans.MiniOSHelper.desktop \
    "$pkgdir/usr/share/applications/org.evans.MiniOSHelper.desktop"
  install -Dm644 org.evans.MiniOSHelper.metainfo.xml \
    "$pkgdir/usr/share/metainfo/org.evans.MiniOSHelper.metainfo.xml"
  install -Dm644 org.evans.MiniOSHelper.svg \
    "$pkgdir/usr/share/icons/hicolor/scalable/apps/org.evans.MiniOSHelper.svg"
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
