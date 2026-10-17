**WEB-17 browser and gate evidence**

The preview uses the package theme and mock props. Mock callbacks verify submission, retained values after failure, and focus restoration. Backend persistence belongs to INT-1. The temporary preview route is removed before each commit.

Chrome checks cover initial name focus, first-invalid-field focus, Escape dismissal, pending dismissal prevention, and description-field error focus. Every captured dialog fits its viewport without horizontal overflow. [Browser measurements](browser-checks.csv) include submit-button text contrast in normal, hover, error, and pending states. All 20 measurements exceed 4.5:1. The minimum is 4.62:1.

| Scheme and viewport | Empty | Entered values | Pending | Request failure | Required name |
| --- | --- | --- | --- | --- | --- |
| Light, 1280 × 900 | [Image](light-desktop-empty.png) | [Image](light-desktop-data.png) | [Image](light-desktop-pending.png) | [Image](light-desktop-error.png) | [Image](light-desktop-invalid.png) |
| Dark, 1280 × 900 | [Image](dark-desktop-empty.png) | [Image](dark-desktop-data.png) | [Image](dark-desktop-pending.png) | [Image](dark-desktop-error.png) | [Image](dark-desktop-invalid.png) |
| Light, 320 × 740 | [Image](light-narrow-empty.png) | [Image](light-narrow-data.png) | [Image](light-narrow-pending.png) | [Image](light-narrow-error.png) | [Image](light-narrow-invalid.png) |
| Dark, 320 × 740 | [Image](dark-narrow-empty.png) | [Image](dark-narrow-data.png) | [Image](dark-narrow-pending.png) | [Image](dark-narrow-error.png) | [Image](dark-narrow-invalid.png) |

[Successful keyboard submission](success-keyboard.webm) verifies dismissal and focus restoration after the mock callback. [Failed keyboard submission](failure-keyboard.webm) verifies retained name and description before Escape restores focus to the invoker.

The standalone web gates pass: [lint](lint.txt), [typecheck](typecheck.txt), [eleven component tests](tests.txt), and [production build](build.txt). The focused creation-dialog run passes all five owned interaction cases. The comment and wording checker passes for all changed TypeScript files.

The independent CI export verifies `npm ci` and [all eleven web tests](isolated-web-tests.txt) without the monorepo. The export also runs the [complete Python suite](python-tests.txt) with its own lockfile and optional web dependencies.

The Python run passes 694 tests with one slow test deselected by the configured lane. The final run reports two dependency deprecation warnings. An earlier run also emits aiosqlite teardown warnings. The scoped change review has no remaining findings after adding keyboard coverage for Cancel and formatting the four conditional expressions. Comment cleanup has no located documentation findings.

[Transition focus checks](transition-focus.txt) verify initial focus and preserve an active description field through the opening transition in both schemes at 1280px and 320px.
