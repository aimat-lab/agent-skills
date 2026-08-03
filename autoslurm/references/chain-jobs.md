# Chain jobs (automatic resume)

Load this when work needs to outlive the cluster's walltime limit, or when a
chain stopped before the work was finished.

Most HPC clusters cap job walltime well below the length of a long training run
or simulation. AutoSlurm's answer is a **chain**: each job runs until it is near
the limit, checkpoints, and leaves behind a note saying how to continue. aslurm
sees the note and submits the next job. This repeats indefinitely until no task
leaves a note.

## The mechanism

Every job script aslurm generates has a tail that, after all tasks in the job
have terminated, checks for resume sentinels:

```
./.aslurm/${SLURM_JOB_ID}_*.resume
```

If any exist, it submits the job's `resume_N.sh` with `PREVIOUS_SLURM_ID` set.
If none exist, the chain ends. That is the whole contract — **a chain continues
if and only if a `.resume` file is present**, so debugging always reduces to
"was the file written, in the right place, before the job ended?"

`write_resume_file` writes to
`./.aslurm/<SLURM_JOB_ID>_<SLURM_SUBMIT_TASK_INDEX>.resume`, where the task index
comes from an environment variable aslurm sets per packed task. So in a
multi-task job each task gets its own sentinel and its own resume command, and
the next job re-runs **only** the tasks that asked to continue.

## Writing the script side

```python
from auto_slurm.helpers import start_run, write_resume_file

timer = start_run(time_limit=10)   # hours

for i in range(start_iter, max_iter):

    ...  # one unit of work

    if timer.time_limit_reached() and i < max_iter - 1:
        save_checkpoint("ckpt.pt")          # checkpoint FIRST
        write_resume_file(
            f"python main.py --checkpoint ckpt.pt --start_iter {i + 1}"
        )
        break
```

Points that matter:

- **`time_limit` is in hours** and is compared against wall time since
  `start_run()` — it is a plain timer, not a Slurm query. Set it meaningfully
  below the config's `time` filler so there is room to checkpoint after the
  check trips. A 24 h job with `time_limit=23.5` may not have time to write a
  large checkpoint.
- **The check only runs where you put it.** A long-running inner operation that
  overshoots the walltime is killed mid-work with no resume file, and the chain
  ends silently. Check between units of work small enough to fit in the slack.
- **Checkpoint before writing the resume file.** The resume command names a
  checkpoint; if the job dies between the two calls, the next job starts from a
  file that does not exist.
- **The resume command is a plain string.** It is re-run verbatim, so it must be
  valid from the submit directory and must carry everything needed to pick up —
  typically checkpoint path plus a start index.
- `write_resume_file` raises `RuntimeError` if `SLURM_JOB_ID` is unset, i.e. when
  run outside Slurm. Guard it if the same script is also run locally.

## ⚠️ The working-directory trap

Both the sentinel path (`./.aslurm/...`) and the resume command's own execution
are **relative to the current working directory**. A task that `os.chdir()`s into
a per-run output directory — common in experiment frameworks — writes its
sentinel into `<run_dir>/.aslurm/`, where the job script does not look. The chain
ends silently and looks exactly like a job that simply finished.

Change back before calling `write_resume_file`, or resolve paths up front and do
not `chdir` at all.

## Debugging a chain that stopped

1. **Was a sentinel written?** Look in `.aslurm/` in the submit directory for
   `<jobid>_*.resume`. Absent → the script never called `write_resume_file`
   (killed mid-unit, `chdir`, or the time check never tripped).
2. **Did the task get killed rather than exiting cleanly?** Check the task's
   `slurm-<jobid>*.out` for a Slurm `TIME LIMIT` / `CANCELLED` line. If so, the
   `time_limit` is too close to the config's `time`.
3. **Did the follow-up job get submitted but fail immediately?** It is a normal
   job — find it by ID and read its `slurm-*.out`. A resume command referencing a
   checkpoint that was never written shows up here.
4. **Only some tasks continued?** That is by design — each task's sentinel is
   independent. Confirm which indices wrote one; the numbering matches the
   `_<taskindex>` suffix on the log files.

## When not to chain

Chaining adds a failure mode (silent early termination) to every long run. If the
work fits in one walltime, do not chain it. If it does not, consider whether the
per-unit checkpoint is cheap enough that a plain requeue-on-preemption would do
the same job with less machinery.
