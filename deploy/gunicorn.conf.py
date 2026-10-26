"""
Gunicorn configuration file for EC2 (behind nginx).
"""
import multiprocessing

bind = 'unix:/run/gunicorn/ecommerce.sock'
workers = multiprocessing.cpu_count() * 2 + 1
timeout = 30
accesslog = '-'
errorlog = '-'
