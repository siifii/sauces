# test/sauces

Render tests written by Sauces' verify step (`/sauces:verify`). Each one pumps a built
screen in every designed state and, when run with
`--dart-define=SAUCES_RENDER_DIR=<dir>`, saves screenshots for scoring against the
design. Without that define they run as ordinary widget tests.

Sauces updates the files it generated here; it never overwrites one you wrote.
