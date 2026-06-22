.PHONY: run embed refresh queries test view install-schedule

run:
	python3 scripts/github_xhs_daily.py run

embed:
	python3 scripts/github_xhs_daily.py embed

refresh: run embed

queries:
	python3 scripts/github_xhs_daily.py queries

test:
	python3 -m unittest discover -s tests

view:
	python3 -m http.server 8787 --bind 127.0.0.1

install-schedule:
	bash scripts/install_daily_launchd.sh
