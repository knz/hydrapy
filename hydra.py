#! /usr/bin/env python

# To use:
#
#   # test the base seq implementation (Box,Seq,Top)
#   python hydra.py seq
#
#   # test the base mult implementation (Box+mult, Seq, Top), with a box with multiplicity N
#   python hydra.py mult N
#   #              (0 <= N <= 4)
#
#   # test the sync implementation (Box+mult,Seq,Top,Sync)
#   python hydra.py sync
#
# Optionally: set env var VERBOSE for details

import sys
import os
from colors import *

INFINITY = 10000

# ------- some logging utilities
debug = os.getenv('VERBOSE')
ilevel = 0
continued = False
def log(msg):
    global ilevel, continued
    if debug is not None:
        if continued is True:
            continued = False
            msg = '>' + msg
        print >>sys.stderr, '--', ('|  ' * ilevel) + msg

def enter(msg):
    global ilevel
    log(msg + ':')
    ilevel += 1

def leave(obj = None):
    global ilevel
    log('<< %r' % obj)
    ilevel -= 1
    log('')
    return obj

def tailcall():
    global ilevel, continued
    log ('%s.. (tailcall)%s' % (cDARK, cNORMAL))
    continued = True
    ilevel -= 1

# --------- basic objets/functions

# record = dict
#   keys = types
#   values = values

class Record(dict):
    def __repr__(self):
        return '%s%s%s' % (cGREEN, dict.__repr__(self), cNORMAL)

class Container(object):
    __slots__ = (  
        'next',   # next in sub-stream sequence
        'record', # record data 
        'pos',    # position of the container in terms of the index of the last network element that it was output from
        'pli',    # predecessor's lower index, ie the minimum pos value of all the container's predecessors
        )


    def __repr__(self):
        s = ''
        c = self
        while c is not None:
            s += '[%r | pos %s%r%s pli %s%r%s]%s@%x%s ' % (c.record,
                                                           cBLUE, c.pos, cNORMAL,
                                                           cBLUE, c.pli, cNORMAL,
                                                           cDARK, id(c), cNORMAL)
            c = c.next
        return s

def createContainer():
    c = Container()
    c.next = None
    c.record = None
    c.pos = 0
    c.pli = 0

    log("createContainer -> %r" % c)
    return c

def markAsFirst(c):
    enter("markAsFirst(%r)" % c)
    c.pli = INFINITY
    log("c -> %r" % c)
    leave()    

def markNextPos(c):
    enter("markNextPos(%r)" % c)
    c.next.pli = min(c.pli, c.pos)
    log("c -> %r" % c)
    leave()

def isFirst(c):
    enter("isFirst(%r)" % c)
    return leave(c.pli == INFINITY)

def handleInput(cont):
    enter('handleInput')

    t = createContainer()
    markAsFirst(t)

    hasinput = True
    while hasinput:
        line = sys.stdin.readline()
        if line == '':
            hasinput = False
        else:
            log("handleInput -> %r" % line)
            t = insertContainer(cont, t, Record({'str': line}))

    log("handleInput: EOF")
    return leave()

def spawnThread(cont, c):
    # FIXME: for now inoperative
    return False

def insertContainer(cont, c, r):
    enter('insertContainer')
    cp = createContainer()
    
    cp.next = c.next
    c.next = cp

    markNextPos(c)

    c.record = r
    log("update rec: c -> %r" % c)

    # LOGIC FOR CONCURRENCY HERE
    if not spawnThread(cont, c): 
        cont(c) 
        
    return leave(cp)


def writeOutput(record):
    print record

def freeContainer(c):
    # in python nothing to do, just drop ref
    log("freeContainer(%r)" % c)

def propagateFirst(c):
    c.next.pli = INFINITY

def handleOutput(c):
    enter('handleOutput(%r)' % c)

    # FIXME: "wait until isFirst(c)"
    while not isFirst(c):
        # FIXME: maybe yield here somehow?
        pass

    log("handleOutput -> %r" % c)
    writeOutput(c.record)
    propagateFirst(c)
    freeContainer(c)

    return leave()

def hset(s):
    if type(s) != set:
        s = set(s)
    return tuple(s)

# -------- Network tree --------

class Top(object):
    def __init__(self, N):
        self.N = N

class Seq(object):
    def __init__(self, N, M):
        self.N = N
        self.M = M

class Box(object):
    def __init__(self, f):
        # f: box function
        # prototype: f(outf, record)
        self.f = f        

class Out(object):
    pass

class Sync(object):
    def __init__(self, K):
        self.K = K

class Star(object):
    def __init__(self, gamma, N):
        self.gamma = gamma
        self.N = N

class Par(object):
    def __init__(self, sigma, N, M):
        self.sigma = sigma
        self.N = N
        self.M = M

class Bling(object):
    def __init__(self, N, tag):
        self.N = N
        self.tag = tag

# -------- hydra C_{seq} -------

def modifyRecord(f, c):
    # apply box function to record, replace result
    enter("modifyRecord(%r)" % c)

    d = [None]
    def outf(r):
        enter("outf(%r)" % r)
        d[0] = r
        leave()

    f(outf, c.record)

    c.record = d[0]
    log("update rec: c -> %r" % c)

    return leave(c)

def Box_seq(f):
    def boxf(c):
        enter("%sbox[%s]%s(%r)" % (cBRIGHT, f.__name__, cNORMAL, c))

        tailcall()
        return modifyRecord(f, c) # tailcall
    return boxf

def Seq_seq(N, M):
    def seqf(c):
        enter("%sseq[%r,%r]%s(%r)" % (cBRIGHT, N, M,  cNORMAL, c))
        
        m = N(c)

        tailcall()
        return M(m) # tailcall
    return seqf

def Out_seq():
    def outf(c):
        enter("out(%r)" % c)

        tailcall()
        return handleOutput(c) # tailcall
    return outf

def Top_seq(N):
    def topf():
        enter("top[%r]" % N)

        cont = Seq_seq(N, Out_seq())

        tailcall()
        return handleInput(cont) # tailcall

    return topf

# test code
if __name__ == "__main__" and sys.argv[1] == 'seq':
    print "testing seq: network = box(stripnl)..box(wrapcolon)"

    def stripnl(outf, s):
        # {str} -> {str}
        enter("stripnl(%r)" % s)
        l = s['str'].rstrip()
        outf(Record({'str': l}))
        leave()

    def wrapcolon(outf, s):
        # {str} -> {str}
        enter("wrapcolon(%r)" % s)
        l = ':' + s['str'] + ':'
        outf(Record({'str': l}))
        leave()


    net = Top_seq(Seq_seq(Box_seq(stripnl), Box_seq(wrapcolon)))

    net()


# -------- hydra C_{mult} -------

'''
# disabled, replaced by Box_mult below
def Box_mult_p(f):
    def boxf(cont, c):
        enter("box[%s](%r, %r)" % (f.__name__, cont, c))
        outlist = []
        def outf(r):
            enter("outf(%r)" % r)
            outlist.append(r)
            return leave()
        f(outf, c.record)
        r = handleMult(cont, c, outlist) # tailcall
        return leave(r)
    return boxf
'''

def Box_mult(f):
    # this implementation inlines the handleMult() function
    # to avoid constructing a list with the output records;
    # this is needed to support boxes with "infinite" number of output records.

    def boxf(cont, c):
        enter("box[%s](%r, %r)" % (f.__name__, cont, c))
        d = [c, None]
        def outf(r):
            enter("outf(%r)" % r)
            c, prevrec = d
            if prevrec is not None:
                c = insertContainer(cont, c, prevrec[0])
            d[0:2] = (c, (r,))
            leave()

        f(outf, c.record)
        
        c, lastrec = d
        if lastrec is None:
            tailcall()
            return markAsDone(c) # tailcall
        else:
            c.record = lastrec[0]
            log("update rec: c -> %r" % c)

            tailcall()
            return cont(c)      # tailcall
            
    return boxf

def Seq_mult(N, M):
    def seqf(cont, c):
        enter("seq[%r,%r](%r, %r)" % (N, M, cont, c))
        def cont_N(cp):
            enter("cont_N(%r)" % cp)

            tailcall()
            return M(cont, cp) # tailcall

        tailcall()
        return N(cont_N, c) # tailcall

    return seqf

def Top_mult(N):
    def topf():
        enter("top[%r]" % N)
        def cont_out(cp):
            enter("cont_out(%r)" % cp)
            tailcall()
            return handleOutput(cp) # tailcall

        def cont_in(c):
            enter("cont_in(%r)" % c)
            tailcall()
            return N(cont_out, c) # tailcall

        tailcall()
        return handleInput(cont_in) # tailcall

    return topf

def markAsDone(c):
    enter("markAsDone(%r)" % c)
    c.pos = INFINITY
    c.next.pli = c.pli
    log("c -> %r" % c)
    leave()

'''
def handleMult(cont, c, res):
    enter("handleMult(%r, %r, %r)" % (cont, c, res))
    for i,n in enumerate(res):
        if i == (len(res) - 1):
            c.record = n

            tailcall()
            return cont(c) # tailcall

        c = insertContainer(cont, c, n)

    tailcall()
    return markAsDone(c) # tailcall
'''


# handleMult expanded to iterative form above
def handleMult(cont, c, res):
    enter("handleMult(%r, %r, %r)" % (cont, c, res))
    if len(res) == 0:
        tailcall()
        return markAsDone(c)  # tailcall
    elif len(res) == 1:
        c.record = res[0]
        log("update rec: c -> %r" % c)

        tailcall()
        return cont(c)        # tailcall
    else:
        cp = insertContainer(cont, c, res[0])

        tailcall()
        return handleMult(cont, cp, res[1:]) # tailcall


# test code
if __name__ == "__main__" and sys.argv[1] == 'mult':
    print "testing mult: ",

    def empty(outf, s):
        # {str} -> {str}
        enter("empty(%r)" % s)
        return leave()
        #return []

    def dup(outf, s):
        # {str} -> {str}
        enter("dup(%r)" % s)
        outf(Record({'str' : s['str'] + '1'}))
        outf(Record({'str' : s['str'] + '2'}))
        return leave()


    def dup3(outf, s):
        # {str} -> {str}
        enter("dup3(%r)" % s)
        outf(Record({'str' : s['str'] + '1'}))
        outf(Record({'str' : s['str'] + '2'}))
        outf(Record({'str' : s['str'] + '3'}))
        return leave()


    def stripnl(outf, s):
        # {str} -> {str}
        enter("stripnl(%r)" % s)
        outf(Record({'str' : s['str'].rstrip()}))
        return leave()

    def wrapcolon(outf, s):
        # {str} -> {str}
        enter("wrapcolon(%r)" % s)
        outf(Record({'str' : ':' + s['str'] + ':'}))
        return leave()

    if sys.argv[2] == '0':
        print "network = box(empty)..(box(stripnl)..box(wrapcolon))"
        net = Top_mult(Seq_mult(Box_mult(empty), Seq_mult(Box_mult(stripnl), Box_mult(wrapcolon))))
    elif sys.argv[2] == '1':
        print "network = box(stripnl)..box(wrapcolon)"
        net = Top_mult(Seq_mult(Box_mult(stripnl), Box_mult(wrapcolon)))
    elif sys.argv[2] == '2':
        print "network = box(stripnl)..(box(dup)..box(wrapcolon))"
        net = Top_mult(Seq_mult(Box_mult(stripnl), Seq_mult(Box_mult(dup), Box_mult(wrapcolon))))
    elif sys.argv[2] == '3':
        print "network = box(stripnl)..(box(dup3)..box(wrapcolon))"
        net = Top_mult(Seq_mult(Box_mult(stripnl), Seq_mult(Box_mult(dup3), Box_mult(wrapcolon))))
    elif sys.argv[2] == '4':
        print "network = box(stripnl)..((box(dup)..box(wrapcolon))..box(dup))"
        net = Top_mult(Seq_mult(Box_mult(stripnl), Seq_mult(Seq_mult(Box_mult(dup), Box_mult(wrapcolon)), Box_mult(dup))))

    net()



# -------- hydra C_{sync} -------


def Box_sync(f):
    def boxf(cont, c):
        enter("box[%r](%r, %r)" % (f.__name__, cont, c))
        recs = []
        def outf(r):
            enter("outf(%r)" % r)
            recs.append(r)
            leave()
        f(outf, c.record)

        posInc(c)

        tailcall()
        return handleMult(cont, c, recs) # tailcall

    return boxf

def Sync_sync(K):
    def syncf(cont, c):
        enter("sync[%r](%r, %r)" % (K, cont, c))

        tailcall()
        return handleSync(cont, c, K) # tailcall

    return syncf

def Seq_sync(N, M):
    def seqf(cont, c):
        enter("seq[%r,%r](%r, %r)" % (N, M, cont, c))
        def cont_N(cp):
            enter("cont_N(%r)" % cp)
            
            tailcall()
            return M(cont, cp) # tailcall

        tailcall()
        return N(cont_N, c) # tailcall

    return seqf

def Top_sync(N):
    def topf():
        enter("top[%r]" % N)
        def cont_out(cp):
            enter("cont_out(%r)" % cp)

            tailcall()
            return handleOutput(cp) # tailcall

        def cont_in(c):
            enter("cont_in(%r)" % c)
            
            tailcall()
            return N(cont_out, c)

        tailcall()
        return handleInput(cont_in) # tailcall

    return topf

class syncstate(object):
    def __init__(self, pos, K):
        slots = {}
        plimax = {}
        for p in K.pats:
            slots[p] = None
            plimax[p] = 0
        self.slots = slots
        self.plimax = plimax
        self.outputpli = pos
        log("syncstate.init -> %r" % self)


    def __repr__(self):
        return "S@%d(%r)" % (id(self),(self.slots,self.plimax,self.outputpli),)

    def storeRecord(self, H, r):
        enter("syncstate.storeRecord(%r, %r, %r)" % (self, H, r))

        for h in H:
            assert h in self.slots
            assert self.slots[h] is None
            self.slots[h] = r

        log("slots <- %r" % self.slots)
        leave()

    def getPlimax(self, pat):
        assert pat in self.plimax
        return self.plimax[pat]

    def setPlimax(self, pat, val):
        enter("syncstate.setPlimax(%r, %r, %r)" % (self, pat, val))

        assert pat in self.plimax
        self.plimax[pat] = val

        log("plimax <- %r" % self.plimax)
        leave()

    def getOutputpli(self):
        enter("syncstate.getOutputpli(%r)" % (self))
        return leave(self.outputpli)

    def setOutputpli(self, val):
        enter("syncstate.setOutputpli(%r, %r)" % (self, val))
        self.outputpli = val
        log("outputpli -> %r" % val)
        leave()

    def isComplete(self, H):
        # """The procedure isComplete is true if all slots, except
        # those indicated in its second argument, have been filled by
        # calls to storeRecord."""
        enter("syncstate.isComplete(%r, %r)" % (self, H))

        for k,v in self.slots.items():
            if k in H:
                continue
            if v is None:
                return leave(False)

        return leave(True)

    def matchesAll(self, H):
        enter("syncstate.matchesAll(%r, %r)" % (self, H))
        # H is the set of all fields in the synchroncell for which the current record
        # is *the* candidate, ie all slots with a matching pattern that were not filled by predecessors.
        # If H is the entire set of slots, the record matches all patterns of the synchrocell.
        for k in self.slots.keys():
            if k not in H:
                return leave(False)
        return leave(True)


    def combineSyncMatches(self, H, rec):
        # """The procedure isComplete is true if all slots, except
        # those indicated in its second argument, have been filled by
        # calls to storeRecord. If no successor was found and all
        # slots have been filled, the calling thread must continue
        # with the combined result"""
        # -> combine only combines the slots not in H
        enter("syncstate.combineSyncMatches(%r, %r, %r)" % (self, H, rec))

        newrec = dict(rec)
        for k,v in self.slots.items():
            if k in H:
                continue
            for t in k:
                assert t not in newrec
                newrec[t] = v[t]

        return leave(newrec)

all_syncstates = {}

def getSyncState(pos, K):
    if pos not in all_syncstates:
        all_syncstates[pos] = syncstate(pos, K)
    return all_syncstates[pos]

def getPlimax(ss, pat):
    return ss.getPlimax(pat)

def setPlimax(ss, pat, val):
    return ss.setPlimax(pat, val)

def getOutputpli(ss):
    return ss.getOutputpli()

def setOutputpli(ss, pli):
    return ss.setOutputpli(pli)

def propagatePli(c):
    enter("propagatePli(%r)" % c)
    c.next.pli = c.pos
    log("c -> %r" % c)
    leave()
    
def matchesAll(s, H):
    return s.matchesAll(H)

def combineSyncMatches(s, H, rec):
    return s.combineSyncMatches(H, rec)

def storeRecord(s, H, rec):
    return s.storeRecord(H, rec)

def isComplete(s, H):
    return s.isComplete(H)

def isDone(c):
    enter("isDone(%r)" % c)
    return leave(c.pos == INFINITY)
    
def posInc(c):
    enter("posInc(%r)" % c)
    c.pos += 1
    log("c -> %r" % c)
    leave()
    

def handleSync(cont, c, K):
    enter("handleSync(%r, %r, %r)" % (cont, c, K))

    s = getSyncState(c.pos, K)
    log("s <- %r" % s)

    M = K(c.record)
    log("M <- %r" % M)

    H = set()
    pli = c.pli
    while len(M) > 0:
        newM = set(M)
        for p in M:
            plimax = getPlimax(s, p)
            if plimax > pli:
                newM.remove(p)
            elif pli > c.pos:
                newM.remove(p)
                H.add(p)
                plimax = INFINITY
            setPlimax(s, p, max(pli, plimax))
            if c.pli > pli:
                propagatePli(c)
                pli = c.pli
        M = newM
        log("M = %r" % M)

    log("H = %r" % H)

    if len(H) > 0 and not matchesAll(s, H):
        done = False
        while not done:
            done = False
            plimin = getOutputpli(s)

            log("pli = %r, plimin = %r" % (pli, plimin))

            if isComplete(s, H):
                log("isComplete = yes")
                c.record = combineSyncMatches(s, H, c.record)
                done = True

            elif pli > plimin:
                log("pli > plimin")
                storeRecord(s, H, c.record)
                markAsDone(c)
                done = True

            setOutputpli(s, min(pli, plimin))
            log("c.pli = %r, pli = %r" % (c.pli, pli))

            if c.pli > pli:
                propagatePli(c)
                pli = c.pli

            log("-> pli = %r, c = %r" % (pli, c))

    if not done: #isDone(c):
        posInc(c)

        tailcall()
        return cont(c) # tailcall

    leave()


class SyncMatcher(object):
    def __init__(self, patterns):
        # patterns is a set of types, each type is a set of type names
        assert len(patterns) > 0
        self.pats = patterns

    def __repr__(self):
        return ("SM(%r)" % (self.pats,))

    def __call__(self, rec):
        # compute which patterns are matched by rec 

        # quote: 
        #    Here, a record type tr matches a network type tn when tn
        #    contains at least one input variant tv that is equal to
        #    or a supertype (i.e. subset) of tr. This means that a
        #    network does not need all fields and tags in a record.
        tr = rec.keys()

        matches = set()
        for tv in self.pats:
            # tr matches pats if all names in tv are in tr
            failmatch = False
            for t in tv:
                if t not in tr:
                    failmatch = True
                    break
            if not failmatch:
                matches.add(tv)
        return matches
            
        

# test code
if __name__ == "__main__" and sys.argv[1] == 'sync':
    print "testing sync"

    def dup(outf, s):
        # {str} -> {A}|{B}
        enter("dup(%r)" % s)
        outf(Record({'A' : s['str'] + '1'}))
        outf(Record({'B' : s['str'] + '2'}))
        return leave()

    def concat(outf, s):
        # {A,B} -> {str}
        enter("concat(%r)" % s)
        outf(Record({'str' : '<%s:%s>' % (s.get('A','?'), s.get('B','?'))}))
        return leave()

    def stripnl(outf, s):
        # {str} -> {str}
        enter("stripnl(%r)" % s)
        outf(Record({'str' : s['str'].rstrip()}))
        return leave()
    def ident(outf, s):
        # {str} -> {str}
        enter("ident(%r)" % s)
        outf(s)
        return leave()

    if sys.argv[2] == "nosync":
        net = Top_sync(
            Seq_sync(
                Seq_sync(
                    Box_sync(stripnl), 
                    Box_sync(dup)
                    ),
                Box_sync(ident)
                )
            )

    elif sys.argv[2] == "nopat":
        net = Top_sync(
            Sync_sync(SyncMatcher(hset([hset([])])))
            )
    elif sys.argv[2] == "1pat":
        net = Top_sync(
            Sync_sync(SyncMatcher(hset([hset(['str'])])))
            )
    else:
        net = Top_sync(
            Seq_sync(
                Box_sync(dup),
                Sync_sync(SyncMatcher(hset([hset(['A']), hset(['B'])])))
                )
            )

    net()


# -------- C_{hydra} -------


def Box_hydra(f):
    return lambda cont,c : handleMult(cont, c, f(c.record)) # tailcall

def Sync_hydra(K):
    return lambda cont, c: handleSync(cont, c, K) # tailcall



def Seq_hydra(N, M):
    def rf(cont, c):
        cont_M = lambda cp: cont(posQes(cp))
        cont_N = lambda x: cont_M( M((lambda cp: posInc(cp)), x) )
        return N(cont_N, posSeq(c))
    return rf

        
def Par_hydra(sigma, N, M):
    def rf(cont, c):
        contp = lambda cp: contp(posTla(cp))
        left = lambda cp: N(contp, posAlt(cp, 0))
        right = lambda cp: M(contp, posAlt(cp, 1))
        if sigma(c.record) == 0:
            return left(c) # tailcall
        else:
            return right(c) # tailcall
    return rf

def Star_hydra(gamma, N):
    def rf(cont, c):
        def rec(cp):
            if gamma(cp) == True: # gamma must return True to indicate star expansion
                rec(posRepl(cp)) # tailcall
            else:
                cont(posReti(cp)) # tailcall
        return rec(posIter(c))
    return rf

def Bling_hydra(N, tag):
    def rf(cont, c):
        contp = lambda cp: cont(posTla(cp))
        cp = posAlt(c, c.record[t])
        return N(contp, cp)
    return rf

def Top_hydra(N):
    return lambda: handleInput(lambda c: N((lambda cp: handleOutput(cp)), c))


        
                            
        
