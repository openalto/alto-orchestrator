all:
	/home/ubuntu/Env/unicorn/bin/python setup.py install
	/home/ubuntu/Env/unicorn/bin/gunicorn -b 0.0.0.0:6666 -w 1 orchestrator.app:app
