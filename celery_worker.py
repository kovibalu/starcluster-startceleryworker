import pipes

from starcluster import threadpool
from starcluster.clustersetup import ClusterSetup
from starcluster.logger import log


class WorkerSetup(ClusterSetup):

    @property
    def pool(self):
        if not getattr(self, '_pool', None):
            self._pool = threadpool.get_thread_pool(size=20, disable_threads=False)
        return self._pool


class StartCeleryWorker(WorkerSetup):

    def __init__(
            self,
            git_sync_dir,
            worker_dir,
            remount_dir=None,
            queue='celery',
            celery_cmd='celery',
            concurrency=None,
            app=None,
            broker=None,
            ld_library_path='/usr/local/lib',
            heartbeat_interval=5,
            maxtasksperchild=1,
            Ofair=True,
            loglevel='info',
            user='ubuntu',
            tmux_history_limit=8000,
    ):

        self._user = user

        if git_sync_dir:
            self._sync_cmd = "; ".join([
                "sudo mount -o remount %s" % qd(remount_dir) if remount_dir else "echo no remount",
                "cd %s" % qd(git_sync_dir),
                "git pull",
                "git submodule init",
                "git submodule update",
            ])
        else:
            self._sync_cmd = None

        celery_args = [
            qs(celery_cmd), 'worker',
            '--hostname', qs('%%h-%s' % queue),
        ]
        if queue:
            celery_args += ['-Q', qs(queue)]
        if app:
            celery_args += ['--app', qs(app)]
        if broker:
            celery_args += ['--broker', qs(broker)]
        if maxtasksperchild:
            celery_args += ['--maxtasksperchild', qs(maxtasksperchild)]
        if concurrency:
            celery_args += ['--concurrency', qs(concurrency)]
        if loglevel:
            celery_args += ['--loglevel', qs(loglevel)]
        if heartbeat_interval:
            celery_args += ['--heartbeat-interval', qs(heartbeat_interval)]
        if Ofair:
            celery_args += ['-Ofair']

        celery_cmd = "; ".join([
            # (use double quotes so that bash expands $LD_LIBRARY_PATH)
            'export LD_LIBRARY_PATH="' + ld_library_path + ':$LD_LIBRARY_PATH"',
            'cd %s' % qd(worker_dir),
            ' '.join(x for x in celery_args),
        ])

        tmux_session = "celery-" + queue
        self._start_cmd = "; ".join([
            "tmux kill-session -t %s" % qs(tmux_session),
            "sudo mount -o remount %s" % qd(remount_dir) if remount_dir else "echo no remount",
            "tmux new-session -s %s -d %s" % (qs(tmux_session), qs(celery_cmd)),
            "tmux set-option -t %s history-limit %s" % (qs(tmux_session), qs(tmux_history_limit)),
        ])

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        run_cmd(node, self._start_cmd, self._user)

    def run(self, nodes, master, user, user_shell, volumes):
        if self._sync_cmd:
            run_cmd(master, self._sync_cmd, self._user, silent=False)
        for node in nodes:
            self.pool.simple_job(
                run_cmd, args=(node, self._start_cmd, self._user), jobid=node.alias)
        self.pool.wait(len(nodes))


class KillCeleryWorker(WorkerSetup):

    def __init__(self, user='ubuntu', queue='celery'):
        tmux_session = "celery-" + queue
        self._kill_cmd = "tmux kill-session -t '%s'" % tmux_session

    def run(self, nodes, master, user, user_shell, volumes):
        for node in nodes:
            self.pool.simple_job(
                run_cmd,
                args=(node, self._kill_cmd, self._user),
                jobid=node.alias,
            )
        self.pool.wait(len(nodes))


def qd(s):
    """ Quote a directory string with double-quotes to allow $variables """
    if s is not None:
        s = str(s).strip()
        if s.startswith('~'):
            s = "$HOME" + s[1:]
        return '"%s"' % s
    else:
        return ''


def qs(s):
    """ Strip and quote-escape a string """
    if s is not None:
        return pipes.quote(str(s).strip())
    else:
        return ''


def run_cmd(node, cmd, user, silent=True):
    log.info("%s@%s: %s" % (user, node.alias, cmd))
    if user != 'root':
        node.ssh.switch_user(user)
    node.ssh.execute(cmd, silent=silent)
    if user != 'root':
        node.ssh.switch_user('root')
