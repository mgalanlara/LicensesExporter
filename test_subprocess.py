import subprocess

p = subprocess.Popen(["lsmon","ucolic01.ctx.uco.es"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
#p.stdin.write('\n')
#p.stdin.close()
print(p.communicate()[0])

