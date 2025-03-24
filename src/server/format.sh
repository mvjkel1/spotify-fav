#!/bin/bash 
set -x

ruff format app --line-length 100
ruff format tests --line-length 100
