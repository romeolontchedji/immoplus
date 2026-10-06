.PHONY: hooks verifier test-outils tester-hooks
hooks:
	git config core.hooksPath .githooks
verifier:
	outils/verifier_tout.sh
test-outils:
	python3 -m unittest discover -s outils/tests -q
tester-hooks:
	bash outils/tester_hooks.sh
