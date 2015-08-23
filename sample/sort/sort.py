import sys
import os
from veriloggen import *

def mkSort(numports=4):
    m = Module('sort')
    width = m.Parameter('WIDTH', 32)
    clk = m.Input('CLK')
    rst = m.Input('RST')
    inputs = [ m.Input('input_' + str(i), width) for i in range(numports) ] 
    outputs = [ m.Output('output_' + str(i), width) for i in range(numports) ]
    kick = m.Input('kick')
    busy = m.OutputReg('busy')
    registers = [ m.Reg('registers_' + str(i), width) for i in range(numports) ]
    for i in range(numports): m.Assign(outputs[i](registers[i]))
    
    _i = [0]
    def mk_pair():
        s = m.Wire('small_' + str(_i[0]), width)
        l = m.Wire('large_' + str(_i[0]), width)
        _i[0] += 1
        return s, l

    def prim_net(a, b):
        s, l = mk_pair()
        m.Assign(s( Cond(a < b, a, b) )) # small
        m.Assign(l( Cond(a < b, b, a) )) # large
        return s, l

    def chain_net(regs, fsm, e):
        x = regs[0]
        for i in range(e):
            s, l = prim_net(x, regs[i+1])
            fsm.add( regs[i](s) )
            x = l
        fsm.add( regs[e](x) )
        for i in range(e + 1, len(regs)):
            fsm.add( regs[i](regs[i]) )
        fsm.goto_next()

    # build up
    fsm = lib.FSM(m, 'fsm')
    idle = fsm.current()

    # init state
    fsm.add(*[registers[i](inputs[i]) for i in range(numports)], cond=kick)
    fsm.add(busy(1), cond=kick)
    fsm.goto_next(cond=kick)

    # connect network
    for i in range(numports):
        chain_net(registers, fsm, numports-i-1)

    # finalize
    fsm.add(busy(0))
    fsm.goto(idle)

    init = [ busy(0) ] + [ r(0) for r in registers ] + [ fsm.set_init() ]

    # import assignment into always statement
    m.Always(Posedge(clk))(
        If(rst)(
            *init
        ).Else(
            fsm.to_case()
        ))
    
    return m

if __name__ == '__main__':
    sort = mkSort()
    verilog = sort.to_verilog()
    print(verilog)