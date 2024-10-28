# tasks.py
from invoke import task

@task
def setup(c):
    """Install npm dependencies"""
    c.run("npm install")

@task
def profile(c):
    """Run the data profiling script"""
    c.run("python el.py")

@task
def sources(c):
    """Run npm sources"""
    c.run("npm run sources")

@task
def report(c):
    """Start profiling report"""
    c.run("npm run dev")

@task(setup, profile, sources, report)
def all(c):
    """Run all tasks"""
    pass
