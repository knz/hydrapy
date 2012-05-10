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
from logging import *
from fn import *

# modes
MODE_SEQ = 0
MODE_MULT = 1
MODE_SYNC = 2
mode = MODE_SEQ

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print >>sys.stderr, "usage:", sys.argv[0], "<mode>"
    if sys.argv[1] == "seq":
        mode = MODE_SEQ
    elif sys.argv[1] == "mult":
        mode = MODE_MULT
    elif sys.argv[1] == "sync":
        mode = MODE_SYNC

INFINITY = 10000

def minindex(a, b):
    assert mode > MODE_SEQ
    if mode <= MODE_SYNC:
        # just compare numerically
        return min(a,b)
    else:
        raise NotImplementedError

def maxindex(a, b):
    assert mode > MODE_SEQ
    if mode <= MODE_SYNC:
        # just compare numerically
        return max(a, b)
    else:
        raise NotImplementedError

# --------- basic objets/functions

# record = dict
#   keys = types
#   values = values

class Rec(dict):
    def __repr__(self):
        return '%s%s%s' % (cGREEN, dict.__repr__(self), cNORMAL)

class Container(object):
    #fields:
    #
    #  next: next in sub-stream sequence
    #  record: the record being referenced
    #
    # MODE_SEQ:
    #  first: True if container is the first (ie not a successor)
    #
    # MODE_MULT:
    #  pli, pos: network indices
    #

    def __repr__(self):
        s = ''
        c = self
        while c is not None:

            s += '[%r | ' % c.record

            if mode <= MODE_MULT:
                s += '%s' % ['succ', 'first'][int(c.first)]
                if c.done:
                    s += ' | %sDONE%s' % (cYELLOW, cNORMAL)
            else: 
                s += 'pos %s%r%s pli %s%r%s' % (cBLUE, c.pos, cNORMAL,
                                                cBLUE, c.pli, cNORMAL,)
                if c.pos == INFINITY:
                    s += ' | %sDONE%s' % (cYELLOW, cNORMAL)                    

            if c.deleted:
                s += ' | %sdeleted%s' % (cRED, cNORMAL)

            s += ']%s@%x%s ' % (cDARK, id(c), cNORMAL)
            c = c.next
        return s

    @informobjp(updater = True)
    def __init__(self):
        # createContainer
        self.next = None
        self.record = None

        if mode <= MODE_MULT:
            self.first = False
            self.done = False
        else:
            self.pos = 0
            self.pli = 0

        self.deleted = False

    @informobjp(updater = True)
    def setRec(self, r):
        self.record = r

    @informobj
    def freeContainer(self):
        # in python nothing to do, just drop ref
        # however for checking we will mark it as deleted
        self.deleted = True

    # ---- accessors in use for the "seq" impl ----

    @informobjp(updater = True)
    def markAsFirst(self):
        if mode <= MODE_MULT:
            self.first = True
        else:
            self.pli = INFINITY

    @informobj
    def isFirst(self):
        if mode <= MODE_MULT:
            return self.first
        else:
            return self.pli == INFINITY

    @informobjp(updater = True)
    def propagateFirst(self):
        thenext = self.next
        while thenext.isDone():
            thenext = thenext.next
            thenext.freeContainer()

        thenext.markAsFirst()

    @informobjp(updater = True)
    def markNextPos(self):

        assert not self.next.isDone()

        if mode <= MODE_MULT:
            self.next.first = False
        else:
            self.next.pli = minindex(self.pli, self.pos)

    # ---- accessors in use for the "mult" impl ----

    @informobjp(updater = True)
    def markAsDone(self):
        assert mode > MODE_SEQ

        assert not self.isDone()

        if mode <= MODE_MULT:
            self.done = True
        else:
            self.pos = INFINITY

            # " After the container at the head of the cons-list reaches its end, markAsDone propa- gates its pli-value to its successor. " (7.4.1)
            self.next.pli = self.pli
        
    # ---- accessors in use for the "sync" impl ----

    @informobjp(updater = True)
    def posInc(self):
        assert mode > MODE_SEQ
        if mode <= MODE_SYNC:
            self.pos = self.pos + 1
        else:
            raise NotImplementedError

    @informobjp(updater = True)
    def propagatePli(self):
        assert mode > MODE_MULT

        thenext = self.next
        while thenext.done:
            thenext = thenext.next
            thenext.freeContainer()

        thenext.pli = self.pos

    @informobj
    def isDone(self):
        if mode <= MODE_MULT:
            return self.done
        else:
            return self.pos == INFINITY

@inform
def insertContainer(cont, c, r):
    cp = Container()

    cp.next = c.next
    c.next = cp

    c.markNextPos()

    c.setRec(r)

    if not spawnThread(cont, c): 
        cont(c) 

    return cp


@inform
def handleInput(cont):

    t = Container()

    t.markAsFirst()

    hasinput = True
    while hasinput:
        line = sys.stdin.readline()
        if line == '':
            hasinput = False
        else:
            log("read input: %r", line)
            t = insertContainer(cont, t, Rec({'str': line}))

    log("read input: EOF")
    

@inform
def spawnThread(cont, c):
    # FIXME: for now inoperative
    return False

def writeOutput(record):
    print record

@inform
def handleOutput(c):
    # FIXME: "wait until isFirst(c)"
    while not c.isFirst():
        # FIXME: maybe yield here somehow?
        pass

    log("c = %r",  c)

    writeOutput(c.record)

    c.propagateFirst()
    c.freeContainer()

    # simply return

def hset(s):
    if type(s) != set:
        s = set(s)
    return tuple(s)

# -------- hydra C_{seq} -------

@inform
def modifyRec(f, c):
    # apply box function to record, replace result


    f(outf, c.record)

    c.record = d[0]
    log("update rec: c -> %r" % c)

    return leave(c)

def Box_seq(f):

    @informp(f)
    def boxf(c):

        # the box function wants to use a function "outf(X)" with
        # the intended meaning to "output record X". So we create
        # a python list to "contain" the record until the box
        # function terminates.    
        d = [None]
        @inform
        def outf(r):
            d[0] = r

        # call the box function
        f(outf, c.record)

        # update the container
        c.setRec(d[0])

        return c

    return boxf

def Seq_seq(N, M):

    @handletc
    @informp(N,M)
    def seqf(c):
        return tailcall(M, N(c))

    return seqf

def Out_seq():

    @handletc
    @inform
    def outf(c):
        return tailcall(handleOutput, c)

    return outf

def Top_seq(N):

    @handletc
    @informp(N)
    def topf():

        cont = Seq_seq(N, Out_seq())
        
        return tailcall(handleInput, cont)

    return topf

# test code
if __name__ == "__main__" and sys.argv[1] == 'seq':
    print "testing seq: network = box(stripnl)..box(wrapcolon)"

    @inform
    def stripnl(outf, s):
        # {str} -> {str}
        l = s['str'].rstrip()
        outf( Rec({'str': l})) 


    @inform
    def wrapcolon(outf, s):
        # {str} -> {str}
        l = ':' + s['str'] + ':'
        outf( Rec({'str': l}) )


    net = Top_seq(Seq_seq(Box_seq(stripnl), Box_seq(wrapcolon)))


    net()


# -------- hydra C_{mult} -------

'''
# disabled, replaced by Box_mult below
def Box_mult_p(f):
    @handletc
    @informp(f)
    def boxf(cont, c):
        outlist = []

        @inform
        def outf(r):
            outlist.append(r)

        f(outf, c.record)

        return tailcall(handleMult, cont, c, outlist)

    return boxf
'''

def Box_mult(f):
    # this implementation inlines the handleMult() function
    # to avoid constructing a list with the output records;
    # this is needed to support boxes with "infinite" number of output records.

    @handletc
    @informp(f)
    def boxf(cont, c):

        d = [c, None]

        @inform
        def outf(r):
            c, prevrec = d
            if prevrec is not None:
                c = insertContainer(cont, c, prevrec[0])
            d[0:2] = (c, (r,))

        f(outf, c.record)
        
        c, lastrec = d
        if lastrec is None:
            c.markAsDone()
            return
        else:
            c.setRec(lastrec[0])

            return tailcall(cont, c)
            
    return boxf

def Seq_mult(N, M):
    @handletc
    @informp(N,M)
    def seqf(cont, c):

        @handletc
        @inform
        def seqf_cont_N(cp):
            return tailcall(M, cont, cp)

        return tailcall(N, seqf_cont_N, c)

    return seqf

def Top_mult(N):

    @handletc
    @informp(N)
    def topf():

        @handletc
        @inform
        def topf_cont_out(cp):
            return tailcall(handleOutput, cp)

        @handletc
        @inform
        def topf_cont_in(c):
            return tailcall(N, topf_cont_out, c)

        return tailcall(handleInput, topf_cont_in)

    return topf


@handletc
@inform
def handleMult(cont, c, res):

    if len(res) == 0:
        c.markAsDone()
        return

    elif len(res) == 1:
        c.setRec(res[0])

        return tailcall(cont, c)

    else:
        cp = insertContainer(cont, c, res[0])

        return tailcall(handleMult, cont, cp, res[1:])


# test code
if __name__ == "__main__" and sys.argv[1] == 'mult':
    print "testing mult: ",

    @inform
    def empty(outf, s):
        # {str} -> {str}
        pass

    @inform
    def dup(outf, s):
        # {str} -> {str}
        outf(Rec({'str' : s['str'] + '1'}))
        outf(Rec({'str' : s['str'] + '2'}))

    @inform
    def dup3(outf, s):
        # {str} -> {str}
        outf(Rec({'str' : s['str'] + '1'}))
        outf(Rec({'str' : s['str'] + '2'}))
        outf(Rec({'str' : s['str'] + '3'}))

    @inform
    def stripnl(outf, s):
        # {str} -> {str}
        outf(Rec({'str' : s['str'].rstrip()}))

    @inform
    def wrapcolon(outf, s):
        # {str} -> {str}
        outf(Rec({'str' : ':' + s['str'] + ':'}))

    @inform
    def ident(outf, s):
        # {str} -> {str}
        outf(s)

    if sys.argv[2] == '0':
        print "network = box(empty)..(box(stripnl)..box(wrapcolon))"
        net = Top_mult(Seq_mult(Box_mult(empty), Seq_mult(Box_mult(stripnl), Box_mult(wrapcolon))))
    elif sys.argv[2] == '1i':
        print "network = box(ident)..((box(stripnl)..box(wrapcolon))..(box(ident)..box(ident))"
        net = Top_mult(Seq_mult(Box_mult(ident), Seq_mult(Seq_mult(Box_mult(stripnl), Box_mult(wrapcolon)), Seq_mult(Box_mult(ident), Box_mult(ident)))))
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

class Pattern(tuple):
    def __repr__(self):
        return '{%s}' % ', '.join(self)

def Box_sync(f):
    @handletc
    @informp(f)
    def boxf(cont, c):
        # FIXME: unfold handleMult to handle infinite multiplicity here (like with _mult above)

        recs = []
        
        @inform
        def outf(r):
            recs.append(r)

        f(outf, c.record)

        c.posInc()

        return tailcall(handleMult, cont, c, recs) 

    return boxf

def Sync_sync(K):

    @handletc
    @informp(K)
    def syncf(cont, c):
        return tailcall(handleSync, cont, c, K)

    return syncf

def Seq_sync(N, M):

    @handletc
    @informp(N, M)
    def seqf(cont, c):

        @handletc
        @inform
        def seqf_cont_N(cp):
            return tailcall(M, cont, cp)

        return tailcall(N, seqf_cont_N, c) 

    return seqf

def Top_sync(N):

    @handletc
    @informp(N)
    def topf():

        @handletc
        @inform
        def topf_cont_out(c):
            return tailcall(handleOutput, c) 

        @handletc
        @inform
        def topf_cont_in(c):
            return tailcall(N, topf_cont_out, c)

        return tailcall(handleInput, topf_cont_in)

    return topf

class syncstate(object):

    @informobjp(updater = True)
    def __init__(self, pos, K):
        self.pats = tuple(K.pats)
        slots = {}
        plimax = {}
        for p in self.pats:
            slots[p] = None
            plimax[p] = 0
        self.slots = slots
        self.plimax = plimax
        self.outputpli = pos

    def __repr__(self):
        rv = []
        for k in self.pats:
            rv.append('%s : (%r ; %s%r%s)' % (k, self.slots[k], cBLUE, self.plimax[k], cNORMAL))
        return '[ %s | outputpli %s%r%s ]%s@%x%s' % (', '.join(rv), 
                                                     cBLUE, self.outputpli, cNORMAL, 
                                                     cDARK, id(self), cNORMAL)

    @informobjp(updater = True)
    def storeRec(self, H, r):
        for h in H:
            assert h in self.slots
            assert self.slots[h] is None
            self.slots[h] = r

    @informobj
    def getPlimax(self, pat):
        assert pat in self.plimax
        return self.plimax[pat]

    @informobjp(updater = True)
    def setPlimax(self, pat, val):
        assert pat in self.plimax
        self.plimax[pat] = val

    @informobj
    def getOutputpli(self):
        return self.outputpli

    @informobjp(updater = True)
    def setOutputpli(self, val):
        self.outputpli = val

    @informobj
    def isComplete(self, H):
        # """The procedure isComplete is true if all slots, except
        # those indicated in its second argument, have been filled by
        # calls to storeRec."""

        for k,v in self.slots.items():
            if k in H:
                continue
            if v is None:
                return False

        return True

    @informobj
    def matchesAll(self, H):
        # H is the set of all fields in the synchroncell for which the current record
        # is *the* candidate, ie all slots with a matching pattern that were not filled by predecessors.
        # If H is the entire set of slots, the record matches all patterns of the synchrocell.

        for k in self.pats:
            if k not in H:
                return False
        return True

    @informobj
    def combineSyncMatches(self, H, rec):
        # """The procedure isComplete is true if all slots, except
        # those indicated in its second argument, have been filled by
        # calls to storeRec. If no successor was found and all
        # slots have been filled, the calling thread must continue
        # with the combined result"""
        # -> combine only combines the slots not in H

        firstpat = self.pats[0]
        if self.slots[firstpat] is None:
            assert firstpat in H
            baserec = rec
        else:
            baserec = self.slots[firstpat]
        log("baserec = %r", baserec)

        for k in self.pats[1:]:
            if k in H:
                sourcerec = rec
            else:
                sourcerec = self.slots[k]
            
            for t in k:
                baserec[t] = sourcerec[t]

        return baserec

all_syncstates = {}

@inform
def getSyncState(pos, K):
    if pos not in all_syncstates:
        all_syncstates[pos] = syncstate(pos, K)
    return all_syncstates[pos]
   
@handletc
@inform 
def handleSync(cont, c, K):

    s = getSyncState(c.pos, K)
    log("s = %r", s)

    M = K(c.record)
    log("M := %r", M)

    H = set()
    pli = c.pli

    while len(M) > 0:
        newM = set(M)
        for p in M:
            plimax = s.getPlimax(p)
            if plimax > pli:
                newM.remove(p)
            elif pli > c.pos:
                newM.remove(p)
                H.add(p)
                plimax = INFINITY
            s.setPlimax(p, maxindex(pli, plimax))
            if c.pli > pli:
                c.propagatePli()
                pli = c.pli
        M = newM
        log("M := %r", M)

    log("H = %r" % H)

    if len(H) > 0: # and not s.matchesAll(H):
        done = False
        while not done:
            done = False
            plimin = s.getOutputpli()

            log("pli = %r, plimin = %r", pli, plimin)

            if s.isComplete(H):
                log("isComplete = yes")
                r = s.combineSyncMatches(H, c.record)
                c.setRec(r)
                done = True

            elif pli > plimin:
                log("pli > plimin")
                s.storeRec(H, c.record)
                c.markAsDone()
                done = True

            s.setOutputpli(minindex(pli, plimin))

            log("c.pli = %r, pli = %r", c.pli, pli)

            if c.pli > pli:
                c.propagatePli()
                pli = c.pli

            log("-> pli = %r, c = %r", pli, c)

    if not c.isDone():
        c.posInc()

        return tailcall(cont, c)


class SyncMatcher(object):
    def __init__(self, patterns):
        # patterns is a set of types, each type is a set of type names
        assert len(patterns) > 0
        self.pats = patterns

    def __repr__(self):
        return "[| %s |]" % ', '.join((repr(x) for x in self.pats))

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

    @inform
    def dup(outf, s):
        # {str} -> {A}|{B}
        outf(Rec({'A' : s['str'] + '1'}))
        outf(Rec({'B' : s['str'] + '2'}))

    @inform
    def concat(outf, s):
        # {A,B} -> {str}
        outf(Rec({'str' : '<%s:%s>' % (s.get('A','?'), s.get('B','?'))}))

    @inform
    def stripnl(outf, s):
        # {str} -> {str}
        outf(Rec({'str' : s['str'].rstrip()}))

    @inform
    def ident(outf, s):
        # {str} -> {str}
        outf(s)

    if sys.argv[2] == "nosync1":
        net = Top_sync(
            Seq_sync(
                Box_sync(stripnl), 
                Box_sync(ident)
                )
            )
    if sys.argv[2] == "nosync2":
        net = Top_sync(
            Seq_sync(
                Seq_sync(
                    Box_sync(stripnl), 
                    Box_sync(dup)
                    ),
                Box_sync(ident)
                )
            )

    elif sys.argv[2] == "1pat":
        net = Top_sync(
            Sync_sync(SyncMatcher((Pattern(('str',)),)))
            )
    else:
        net = Top_sync(
            Seq_sync(
                Box_sync(dup),
                Sync_sync(SyncMatcher((Pattern(('A',)), Pattern(('B',)))))
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


        
                            
        
