from nonblock import nonblock_read

# pipe = subprocess.Popen(['someProgram'], stdout=subprocess.PIPE)

# ...

while True:
    data = nonblock_read(pipe.stdout)
    if data is None:
        print 'None'
    elif data:
		# Some data has been read, process it
		# processData(data)
        print data
	# else:
	# 	# No data is on buffer, but subprocess has not closed stream
	# 	idleTask()

# All data has been processed, focus on the idle task
# idleTask()