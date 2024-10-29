# tasks.py
from invoke import task

@task
def load(ctx):
    """Run load.py script"""
    ctx.run("python scripts/load.py")

@task
def pattern(ctx):
    """Run pattern.py script"""
    ctx.run("python scripts/pattern.py")

@task
def summary(ctx):
    """Run summary.py script"""
    ctx.run("python scripts/summary.py")

@task
def sql(ctx):
    """Run sql.py script"""
    ctx.run("python scripts/sql.py")

@task
def all(ctx):
    """Run all scripts in sequence"""
    load(ctx)
    pattern(ctx)
    summary(ctx)
    sql(ctx)
