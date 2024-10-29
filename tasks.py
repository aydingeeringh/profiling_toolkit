# tasks.py
from invoke import task

@task
def load(ctx):
    """Run load.py script"""
    ctx.run("uv run scripts/load.py")

@task
def pattern(ctx):
    """Run pattern.py script"""
    ctx.run("uv run scripts/pattern.py")

@task
def summary(ctx):
    """Run summary.py script"""
    ctx.run("uv run scripts/summary.py")

@task
def sql(ctx):
    """Run sql.py script"""
    ctx.run("uv run scripts/sql.py")

@task
def profile(ctx):
    """Run all scripts in sequence"""
    load(ctx)
    pattern(ctx)
    summary(ctx)
    sql(ctx)

@task
def init(ctx):
    """Initialize the dataprofiling"""
    ctx.run("npm install")
    ctx.run("npm run sources")
    ctx.run("npm run dev")

@task(
    help={
        "name": "Name of the table to delete from profiling data",
    }
)
def delete(ctx, name):
    """
    Delete profiling data for a specific table.
    
    Examples:
        invoke delete -n orders
        invoke del -n customers
    """
    print(f"Deleting profiling data for table: {name}")
    ctx.run(f"uv run scripts/delete.py {name}")

# Register the shorter alias
delete_short = task(name="del")(delete)