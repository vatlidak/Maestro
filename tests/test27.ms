#!maestro
#master("0.0.0.0:6379")
# check use of the operator %
c = 5
d = 8; 
range(8%5).each(var){
	a = Job('print.py', var)
	run(a)
}
range(3).each(var){
	a = Job('print.py', var)
}
