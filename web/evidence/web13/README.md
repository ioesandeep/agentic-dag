**WEB-13 selector verification.**

The temporary preview uses the application theme, built application fonts, and mock catalog props. These checks verify browser selection state. They do not test backend persistence. The preview is removed before committing.

[Browser measurements](browser-checks.json) record zero page errors and zero horizontal overflow at 1280px and 320px in both schemes. [Button contrast measurements](contrast-checks.json) cover normal, hover, focus, and disabled states. All 18 measurements exceed 4.5:1. The minimum is 5.76:1.

| State | Light desktop | Dark desktop | Light narrow | Dark narrow |
| --- | --- | --- | --- | --- |
| Loading | [Image](light-1280-loading.png) | [Image](dark-1280-loading.png) | [Image](light-320-loading.png) | [Image](dark-320-loading.png) |
| No ready repository | [Image](light-1280-empty.png) | [Image](dark-1280-empty.png) | [Image](light-320-empty.png) | [Image](dark-320-empty.png) |
| Sole ready repository | [Image](light-1280-single.png) | [Image](dark-1280-single.png) | [Image](light-320-single.png) | [Image](dark-320-single.png) |
| Several ready repositories | [Image](light-1280-multiple.png) | [Image](dark-1280-multiple.png) | [Image](light-320-multiple.png) | [Image](dark-320-multiple.png) |
| Initial failure | [Image](light-1280-error.png) | [Image](dark-1280-error.png) | [Image](light-320-error.png) | [Image](dark-320-error.png) |
| Refresh failure | [Image](light-1280-refresh.png) | [Image](dark-1280-refresh.png) | [Image](light-320-refresh.png) | [Image](dark-320-refresh.png) |

The [keyboard recording](keyboard-selection.webm) selects a repository and changes the project. The repository choice clears after the project changes. The [focus image](dark-320-keyboard-focus.png) shows the focused repository control at 320px. Browser storage contains only the project preference.

The CI export passes [npm ci](isolated-install.txt), [all web tests](isolated-web-tests.txt), and the [complete Python suite](python-tests.txt) independently of the monorepo.

The final worktree passes [lint](lint.txt), [type checking](typecheck.txt), [all 27 web tests](web-tests.txt), and the [production build](build.txt). The scoped rulebook review has no remaining findings.
