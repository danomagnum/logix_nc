# logix_nc

I had heard rumblings of a logix based CNC system at teched ~~last year~~ many moons ago and thought it was a pretty neat idea.  I thought about it for a while and put my own demo version of it together in my free time over the last week.  Note that all of the gcode in the examples I found by googling "example gcode" and similar - I didn't create any of it.  Also note that some of the lines look jagged in the gifs below but that is due to the refresh rate of the FTView ME screen, 

I did end up getting to look at the rockwell NC code at some point.  It's way more complicated to modify, but it also supports things like using a coordinated servo axis as the spindle to do rigid tapping and such.  If you're looking for a NC solution on logix, reach out to your rockwell rep and ask them about it - then you can decide whether this code or their code is a better fit for your application.


[dino image](gcode6.gif)

The two arrows near the gcode in the image above are from left to right the motion pointer and the look ahead pointer.

It ended up being easier than I expected to do.  It is also way more performant than I expected.  I was concerned that the processor would be too bogged down parsing and interpreting the gcode to execute the motion task, but it ended up not being a problem even with a program that has close points generated from splines and with extremely high feed rates(originally I had a bug that had feedrates that should have been in units/minute being used in units/second so it was running at 6000%).  Logix task monitor showed over 50% idle time on a 1756-L61.

Here are some of the features.

It can handle reading (#) and writing ($) to variables by number (and supports pointers) as well as basic math (+, -, / *). The values returned extend to all commands.

```
#100 reads variable 100
$20 5.0 writes 5 to variable 20
##3 reads the variable 3 then reads the variable pointed at by it.
$#3 #4 reads variable 4 and writes its value to the variable pointed at by variable 3.
$##3 #4 reads variable 4 and writes its value to the variable pointed at by the variable pointed at by variable 3.
M#2 reads variable 2 and does M<v2> so if variable 2 = 00, you get a MOO
```

It also handles comparisons (<, =, >) and an IF operator (?).  
The ? operator reads the value to the right of it (which can be calculated by a variable or a constant).  If the value is >0 the rest of the line to the right is executed.  Otherwise it is skipped.  There is an example of this below.

[user interface](http://danomagnum.com/files/Logix_NC/gcode3.gif)

It handles G00 (rapid), G01 (linear), G02 (cw circle) and G03 (ccw circle).  Although I didn't spend enough time to verify that G02 and G03 are working exactly right, it seems to handle most cases correctly.  G03 and G04 were tricky because once you've got 3 axis coordinate system in logix you can't specify cw or ccw anymore, just "short way round" or "long way round".  I did some math on the xy plane to decide which was was intended and choose appropriately, but something might be off with it.  This should make adding G17, G18, and G19 (circular moves relative to XY, XZ, and YZ planes) easy but I did not bother with them.

It handles tool offsets. As selected by a T word from 0-1024.  G43 can be used to change the tool offsets from the program.

```
N001 T1 ; Select tool offset 1.
...
N100 G43 P10 X0 Y0 Z10; Select tool 10 and set its values to an offset of 0, 0, 10.
```

It handles work offsets G54 - G59.  G10 can be used to configuree offsets on the fly and/or change to an arbitrary offset (0-1024) using a P-value.  You can change work offset 0 (G53 - Machine coords) during program execution but it reverts to all 0's on reset.

```
N001 G10 P30 ; Switch to work offset 30 without changing it
...
N050 G10 X5.0 Y2.3 Z0.1 ; Set the value of the current offset to X=5.0, Y=2.3, and Z=0.1
... 
N100 G10 P100 X10 Y11 Z12 ; Switch to offset 100 and change its values to X=10, Y=11, and Z=12
...
```

gcode5.gif

It handles parenthesis comments and end of line comments (everything after a ; is ignored)

It also handles block skip (/) and op-stop.  Only a / at the first character of a line is a block skip.  Otherwise it is used as a divide operator.

It supports subroutines and subprograms with M97 (jump within program), M98 (jump to seperate routine), M99 (return), and M96 (relative non-returnable jumps).  It does not support L to re-run automatically but that can be handled through the ? operator and M96 as shown below.
It supports 1024 nested subroutine calls shared between within-program "subroutines" and calling external subroutines, of which it supports up to 10 dedicated separate subroutines (of configurable length at the expense of memory) and a short MDI program.
Loading (sub)programs into the controller is handled by a pylogix based python script that requests the controller clear the (sub)program and then re-fills it with data from a computer one line at a time.  The script takes a gcode text file as argument 1 and optional subroutine number as argument 2.  For example "python gcode_loader.py test.gc" would load the file test.gc to the main program whereas "python gcode_loader.py test.gc 3" would load test.gc to subroutine #3.

```
import eip
import time
import sys


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

```

As far as calling subroutines from within a gcode program goes M97, 98, and 99 all push a new program pointer onto the stack that can be returned from.  These are the traditional CNC jump commands.  M96 is different.  It jumps a relative distance and does not add a layer to the stack.  It can be used as follows combined with M97 or M98 to run a subroutine multiple times.

```
N001 $001 10 ; Set variable 1 to 10.
N002 X0 Y0 Z0 ; Home
N003 M98 P01 ; Run subroutine 1
N004 $001 #001 - 1; Decrement counter
N005 ? #001 M96 P-3; Jump back to the move to 0 on line 2
```



The biggest problem I see is that the processor is effectively out of memory.  There are a few ways to correct that.  
The first would be to change the main program, the subroutines, and MDI program to use a custom string type that is a little shorter.  I had considered this but the default length of 82 is actually pretty right-on for a line of gcode.
The next option would be to change the length of the arrays that hold the sub programs to embiggen the main program.
You could also probably get rid of MDI, though it's size is already relatively small.
A more advanced technique would be to load the gcode program in blocks in real time and have the upload program be constantly running and handshaking with the controller as it runs.  At a minimum, hooks would have to be added for the controller to request specific lines of programs for jumping to work properly.

Ultimately it works pretty well.
