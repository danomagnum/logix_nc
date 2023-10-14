import eip
import time
import sys

# note: this is using a super old version of pylogix - modern ones import as pylogix instead of eip.  You'll need to change this.
NC_PLC = eip.PLC('10.81.252.170')

filename = sys.argv[1]
with open(filename, 'r') as f:
	text = f.readlines()
total = len(text)

subload = False
subno = 0

if len(sys.argv) > 2:
	subload = True
	subno = int(sys.argv[2])
	NC_PLC.Write('Program:NC.di_Clear_Subprogram', int(sys.argv[2]))
	


NC_PLC.Write('Program:NC.di_Clear_Program', True)

wait_for_clear = True
while wait_for_clear:
	time.sleep(0.2)
	if not NC_PLC.Read('Program:NC.di_Clear_Program'):
		wait_for_clear = False
		

for i, line in enumerate(text):
	if subload:
		NC_PLC.Write('Program:NC.SubPrograms[{},{}]'.format(subno, i), line)
	else:
		NC_PLC.Write('Program:NC.GcodeProgram[{}]'.format(i), line)
	print '\
{} / {}'.format(i, total),
