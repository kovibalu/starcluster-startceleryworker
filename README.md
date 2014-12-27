StartCeleryWorker
=================

A plugin to start celery workers on every node of a StarCluster cluster.

Each celery worker is contained in a tmux session, so you don't need to worry
about log files taking up too much disk space.  Each worker logs to the screen
on its local tmux session.  Using tmux sessions makes it easier to reliably
kill celery workers.  The tmux session is named `"celery-" + queue`.

### Installation
1. Check out this repository.
2. Add a symlink to `celery_worker.py` in `~/.starcluster/plugins/`.
3. Configure the plugin in `~/.starcluster/config` (see below).

### Typical configuration:
Add this to your `~/.starcluster/config` file:
<pre>
[plugin start_celery_worker]
setup_class = celery_worker.StartCeleryWorker

# The base of the git code repository that the workers use.  The repo and all
# submodules will be updated.
git_sync_dir = ~/repo

# Directory where the celery worker will run
worker_dir = ~/repo/code

# Python package containing the celery app (used by the -A argument for celery)
app = my.celery.app

# Name of the celery queue (default: celery)
queue = celery

# Number of worker processes to run (None to use all processes)
concurrency = None

[plugin kill_celery_worker]
setup_class = celery_worker.KillCeleryWorker
queue = celery
</pre>

Note that you can have multiple plugins with different names (e.g.
`[plugin start_gpu_celery_worker]`, `[plugin start_cpu_celery_worker']`).

When you start a new cluster or add a new node, workers will automatically be
started.  Note that if you change the configuration after starting the cluster,
new nodes will still be added with the old configuration.  If someone knows how
to fix this, please let me know!

### Command line
**Start/restart your workers:**
<pre>
starcluster runplugin start_celery_worker cluster_name
</pre>
If the workers are already started, running start again will re-sync the code,
kill them, and then start them again.

**Kill your workers:**
<pre>
starcluster runplugin kill_celery_worker cluster_name
</pre>


### Other options for start_celery_worker:
Include these under `[plugin start_gpu_celery_worker]`:
<pre>
# Use a different command to start celery, such as with a venv (with respect to
# the path worker_dir)
celery_cmd = ../venv/bin/celery

# Remount the base directory of the NFS filesystem, to be remounted before
# any code is run (this helps ensure it is up to date)
remount_dir = /home

# Use a different broker than the one specified in your config
broker = 'amqp://guest@localhost//'

# Add extra paths to LD_LIBRARY_PATH for the worker
ld_library_paths = /usr/local/lib:/some/other/path

# Use a different heartbeat (in seconds)
heartbeat_interval = 5

# Restart the workers after a different number of tasks (change to be higher if
# you have lots of little tasks)
maxtasksperchild = 1

# Whether to include -Ofair (I find that it helps increase worker utilization).
Ofair = True

# Different log level
loglevel = info
</pre>
