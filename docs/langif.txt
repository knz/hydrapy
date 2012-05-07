=============================
 Language interface clean-up
=============================

:Authors: kena, merijn, frank
:Date: May 2012

:Abstract: This note proposes a new API to manage field data,
   especially from SNet box code, and also from control entities. It
   integrates the "sane" reference semantics proposed by Merijn on the
   snet-dev mailing list on March 15th 2012 and discussed subsequently
   in technical meetings. It also ensures that all APIs can be
   overridden at run-time. The main changes are 1) clear semantics for
   ownership 2) mandatory passing of the execution context as 1st
   argument to all API calls, not only the SNetOut function.

.. contents::

Introduction
============

Objectives
----------

We want to track storage allocated for fields "between" boxes somehow,
so we need some form of "field database" managed outside the box
languages and common between them.

Also we want to support multiple box languages.

In each language we want to support different allocation / destruction
policies for different data types.

Also we want to allow programs to use either "managed" allocation
(outside of the box languages) and "unmanaged" allocation (using the
box language allocator):

- the managed allocation is "better" because it can allow nice tricks
  like allocating storage physically closer to the eventual
  destination of an object.

- however in some cases (eg SAC) the box language may not know
  statically whether to use the managed allocator or its own (private)
  allocator, so we want to be able to capture an object privately
  allocated and put it in the database nonetheless.

Also we want to stop once and for all the tooling headache about *link
order*: If RTS A calls language B, and language B then calls API in
RTS A (eg RTS -> box -> snet_out), the poor linker is often confused
if we want to compile things separately.

Summary of proposal
-------------------

So we introduce the following abstractions:

- a common *field database*, which registers the concrete allocated
  items of data and their reference counters.

- a unique *field reference* type which refers to an entry in the
  field database, with accessors for the actual data.

- Each component in the entire system receives *callbacks* to
  these "management utilities" as arguments when invoked. This has
  the following advantages:

  - we avoid polluting the global namespace with fixed-name functions 

  - we avoid global variables and the question of "who manages what":
    if a component does not receive a pointer to something, that means
    clearly "it does not need to know".

  - we avoid any future linking headache, and we open the
    opportunities to choose different implementations for things using
    dynamic linking.

- a common *concrete type database*, which understands the concrete
  (implementation) types and their various language-specific data
  handlers. The various box language run-times register their types to
  this. It also knows about a few base types, including scalars.

  The concrete type database registers the
  serialization/deserialization, allocation/deallocation functions for
  the individual concrete types. 


Output and logging interface
============================

Box functions as previously receive as first argument a "handle"
followed by the actual field arguments.

However the handle now is not opaque any more. We populate it with the
function pointers to the API that the box can use to interact with the
environment.

We introduce the following declaration in ``langif.h``:

.. code:: c

   struct io_cb {
      const struct io_cb_api *api;
      /* invisible additional fields here
         to identify the calling task, its private state, etc. */
   };

   struct io_cb_api {

      // output function.
      // may fail: the box function should terminate with error in that case.
      // OK is 0, error is non-zero
      int (*out)(const struct io_cb*, ...);
   
      // logging function; will redirect the output to a
      // box-specific output stream.
      void (*log)(const struct io_cb*, int loglevel, const char *fmt, ...);
 
      // proposed logging levels
   #define  LOG_NOTSET   0
   #define  LOG_DEBUG    10   // printf-style debugging
   #define  LOG_INFO     20   // what is being communicated, identifiers, etc
   #define  LOG_WARN     30   // unexpected conditions, can resume
   #define  LOG_ERROR    40   // unexpected condition, will terminate computation prematurely
   #define  LOG_FATAL    50   // unexpected condition, behavior undefined
 
      /* ... other functions here, see below ... */
   };
 
   /* to simplify calling */
   #define svp_out(hnd, ...)           hnd->api->out(hnd, __VA_ARGS__)
   #define svp_log(hnd, lvl, fmt, ...) hnd->api->log(hnd, lvl, fmt, __VA_ARGS__)

For example, a box function with type "{<a>} -> {<x>,<y>,<z>}",
could be written so:

.. code:: c

   int testbox(const struct io_cb* cb,  int a)
   {
      svp_log(cb, LOG_INFO, "textbox received %d", a);
      
      // this box' behavior is to forward 3 copies of the tag
      // and then its value +1 and +2.
 
      return svp_out(cb, a, a, a) &&
             svp_out(cb, a+1, a+1, a+1) &&
             svp_out(cb, a+2, a+2, a+2);
   }
 
Like with the logging function, the box function can return non-zero
to indicate an error has occurred.

For backward compatibility we can define the following preprocessor
macro:

.. code:: c
   
   #define C4SNetOut svp_out

Field management for boxes
==========================

The field database is a system service which knows about fields and
concrete data types. 

It can be *observed* from "outside" (eg for monitoring), and it can be
*used* from "inside" (ie boxes).


To the "inside" it provides the following services:

- organization of data in a common storage, with "smart references"
- "sane" sharing semantics: an object is read-only if there are
  multiple references to it, read-write if there is only one
  reference.
- allocation of new objects
- capture of a non-managed data pointer
- automatic deallocation

For this purpose the ``io_cb`` API structure is extended as follows:

.. code:: c

   // fieldref_t is an opaque integer which names a field data item.
   // The special value 0 means "null reference".
   typedef ... fieldref_t;
 
   // typeid_t is an opaque integer which names a concrete data type.
   typedef ... typeid_t;
 
   struct io_cb_api {
      /* ... out, log already mentioned above .. */
 
      // alloc: creates a fresh new object of the specified type and size.
      fieldref_t (*new)(const struct io_cb*, size_t thesize, typeid_t thetype);
 
      // release: drop the specified reference.
      void (*release)(const struct io_cb*, fieldref_t theref);
 
      // access: retrieve a pointer to the data.
      int (*access)(const struct io_cb*, fieldref_t theref, void **ptr)
 
      // getmd: retrieve object metadata.
      int (*getmd)(const struct io_cb*, fieldref_t theref, size_t *thesize, typeid_t *thetype, size_t *realsize);
 
      // clone: duplicate the object.
      fieldref_t (*clone)(const struct io_cb*, fieldref_t theref);
 
      // wrap: captures an opaque data pointer.
      fieldref_t (*wrap)(const struct io_cb*, typeid_t thetype, size_t size, void* data);
 
      // resize: modify the logical size of the object.
      int (*resize)(const struct io_cb*, fieldref_t theref, size_t newsize);
 
   };

   /* to simplify calling */
   #define svp_release(x, y)     x->api->release(x, y)
   #define svp_access(x, y, z)   x->api->access(x, y, z)
   #define svp_getmd(w, x, y, z) x->api->getmd(w, x, y, z)
   #define svp_clone(x, y)       x->api->clone(x, y)
   #define svp_wrap(w, x, y, z)  x->api->wrap(w, x, y, z)
   #define svp_resize(x, y, z)   x->api->resize(x, y, z)

   
The services have the following semantics:

- ``new``: allocate a fresh object.

  The size is the number of elements of the individual type provided.
  For example with special type "0" (non-aligned bytes) the size
  will specify the number of bytes to allocate.
 
  The actual available types depend on the `Concrete type database`_ discussed later.

  Return value for ``new``:

  - >0: reference to the data item. At that point the object is
    guaranteed writeable (only one reference).
  - 0: (null reference) the allocation has failed.

- ``release``: release the provided reference.

  The object will be deallocated if the provided reference was the
  last one.

- ``access``: access the object's contents.

  Return value:

  - 0: the data is read-only (there is more than one reference to it)
  - 1: the data is read-write (there is exactly one reference to it)
  - -1: the reference is invalid.

  If the reference is valid, ``access`` overwrites ``*theptr``
  with the pointer to the object's contents. If ``theptr`` is NULL,
  ``access`` just tests the number of references.

- ``getmd``: retrieve object metadata.

  ``getmd`` overwrites the variables provided by non-NULL address as
  argument by the corresponding fields metadata:

  - ``*thesize``: requested/logical size (given to ``new``). Set to 0 if
    the data was captured with ``wrap``.
  
  - ``*thetype``: concrete type identifier.

  - ``*moresize``: *actual* allocated size. The difference with
    ``*thesize`` is made because ``new`` may have allocated more bytes
    than requested. These bytes can be used. Set to 0 if the data
    was captured with ``wrap``.

  Return value: as per ``access`` above.

- ``clone``: duplicate the object, return a new reference to the fresh object.

  Return value: as per ``new`` above.

- ``wrap``: capture a data pointer.

  Create a managed entry in the field database and associate it with
  the provided pointer and size. Subsequent calls to ``getmd`` will
  return the provided size.

- ``resize``: modify the logical size.

  When ``new`` has allocated more bytes than requested, the extra
  bytes can be used to "shrink" or "expand" the object contained.
  Shrinking or expanding does not change the *actual* (physical)
  allocated size, returned via ``*realsize`` by ``getmd``. It does
  change ``thesize`` as returned by further calls to ``getmd``.

  Return value:

  - 0: operation successful
  - 1: operation failed because data is read-only (more than 1 reference)
  - -1: possible cases:

    - reference invalid
    - the desired new size does not fit within the actual allocated
      size. In this case the program should make a new allocation and
      release the previous one.
  
  If the data was captured with ``wrap``, resizing will simply modify
  the "size" field. In particular ``resize`` will not call the
  allocation/copy/deallocation functions associated with the concrete
  type. 

Example
-------

We want to make a box "t2l" which takes one tag as input and converts
it to a C "long long".

For this we can write the following code in ``boxes.c``:

.. code:: c

   #include "langif.h"
   
   // signature: {<tag>} -> {ll}
   void t2l(const struct io_cb* cb,  int tag)
   {
       svp_log(cb, LOG_INFO, "hello from t2l, tag = %d", tag);
 
       // allocation by the "environment"
       fieldref_t f = svp_new(cb, sizeof(long long), BYTES_SCALAR_ALIGNED);
 
       // output the field reference; note
       svp_out(cb, f);
 
       // that out does not "take away" ownership; instead it will
       // add new references as needed. So we need to release here as well.
       svp_release(cb, f);
   }

We can make a box which forwards its entire input string as a new
record except for the first character which is capitalized:

.. code:: c

   #include "langif.h"

   // signature: {string} -> {string}
   int capitalize(const struct io_cb* cb,  fieldref_t  string)
   {
       char *str;
       int rw = svp_access(cb, string, &str);
       if (!rw) {
           // can't write, so make a copy.
           string = svp_clone(cb, string);
           svp_access(cb, string, &str);
       }

       // do the update. 
       str[0] = toupper(str[0]);

       svp_out(cb, string);

       // no need to explicitly release. The environment
       // remembers all allocations, and will release all references
       // that were allocated by this box.
       return 0;
   }

Discussion about box ownership
------------------------------

There was a discussion about who's responsible for releasing
references manipulated by boxes.

There are two questions that need answering:

1. who releases the field references that a box gets as input?

   Two options:
  
   a. the box itself, before it terminates.
   b. the environment, automatically after the box terminates.

2. who releases the field references that a box creates
   during its execution?

   Three options:

   a. the box itself, after it sends it via out().
   b. the out() function.
   c. the environment, automatically after the box terminates.

Analysis
````````

About 1a: yields memory leaks if the programmer forgets to do so.

About 1b: yields a potential wasted opportunity in long-running boxes
with the following structure:

.. code:: c
  
   // signature: {bytes} -> {<x>, bytes}
   int examplebox(const struct io_cb* cb,  fieldref_t  x)
   {
      // this box outputs its input record with tag 0,
      // then 1000 fresh records with tag 1.
      svp_out(cb, 0, x);

      for (int i = 0; i < 1000; ++i)
      { 
           fieldref_t f = svp_new(cb, 1, BYTES_UNALIGNED);
           svp_out(cb, 1, f);
      }
      return 0;
   }

When this box runs, the memory for the input field ``x`` will remain
allocated for the entire duration of the box' execution, even though
it is not needed after the initial "out".


About 2a: yields memory leaks if the code forgets to call release.

About 2b: creates a problem if a box wants to output multiple
references to the same field data. For example:

.. code:: c

   // signature: {bytes} -> {bytes}
   int examplebox(const struct io_cb* cb,  fieldref_t  x)
   {
      for (int i = 0; i < 1000; ++i)
           svp_out(cb, x);

      return 0;
   }

This code is invalid: if ``out`` calls release, then after the first
iteration the reference ``x`` would not be valid any more.

About 2c: like 1b above, is inefficient when a long-running box
allocates many objects but only outputs each reference a few times. For example:

.. code:: c

   // signature: {<tag>} -> {bytes}
   int examplebox(const struct io_cb* cb,  int tag)
   {
      for (int i = 0; i < 1000; ++i)
      { 
           fieldref_t f = svp_new(cb, 1, BYTES_UNALIGNED);
           svp_out(cb, f);
      }
      return 0;
   }

In this box, it would be inefficient if the environment waits until
the end before it releases the allocated objects. Also it would create
a memory leak if the box is modified so that the loop never
terminates.

Solution
````````

We want to avoid a solution based on a "shallow copy" API, which would
be highly confusing to box implementors. Instead we want to solve the
problem using only the existing API.

We do this as follows:

- all the references that are given as input to a box function
  are placed on a "clean up" list attached to the box instance. 

- each call to ``new``, ``wrap`` or ``clone`` by a box instance will
  cause the environment to store the reference to the newly allocated
  object in the "clean up" list.

- when the box terminates, the environment walks through the clean up
  list and releases all the references in the list.

- *if and only if the box code calls ``release`` on a reference*, 
  ``release`` will do its work and *also* remove the reference from
  the clean up list.

  The reference is always removed from the clean up list, even if
  there are multiple other references to the object.

With this modification to the semantics of ``release``, the box code
can then *optionally* control deallocation. 

We illustrate with two examples. The first does not use ``release``:

.. code:: c

   // signature: {<tag>} -> {bytes}
   int examplebox(const struct io_cb* cb,  int tag)
   {
      for (int i = 0; i < 1000; ++i)
      { 
           fieldref_t f = svp_new(cb, 1, BYTES_UNALIGNED);
           svp_out(cb, f);
      }

      return 0; 
   }

This loop style accumulates all references implicitly in the clean up
list. All the 1000 fields are only deallocated when the box
terminates.

In contrast:

.. code:: c

   // signature: {<tag>} -> {bytes}
   int examplebox(const struct io_cb* cb,  int tag)
   {
      for (int i = 0; i < 1000; ++i)
      { 
           fieldref_t f = svp_new(cb, 1, BYTES_UNALIGNED);
           svp_out(cb, f);
           svp_release(cb, f);
      }

      return 0; 
   }

The use of ``release`` forces early deallocation, and "remembers" that
the deallocation has taken place by removing the reference from the
clean up list.


.. hint:: Implementation detail.
 
   If a box takes two fields {A,B} as input, both must be separate
   entries in the clean up list because:
   
   - the box code must be able to call ``release`` explicitly on
     either

   - if the box code only calls ``release`` on one, the environment
     must only call ``release`` on the other.

   However in some cases the same object reference x will be passed as
   two separate inputs to a box function, for example with a box
   following a filter which creates two conceptual copies of the same
   field as separate fields in its output record.

   If the clean up list is a linked list on the objects themselves, a
   naive implementation would have a problem: there would be only one
   node on the list even if the object is listed as 2 separate
   arguments of the box.

   So instead each linked list node also stores the number of times
   the object is listed in the input argument list, which is also
   the number of times ``release`` must be called on that node when
   the box ends.

Backward compatibility
----------------------

The APIs proposed above are similar to C4SNet in the following fashion:

.. code:: c

   #define C4SNetCreate(hnd, type, size, data) \
       ((c4snet_data_t*)(void*)svp_wrap(hnd, type, size, data))
   
   #define C4SNetFree(hnd, ptr) \
       svp_release(hnd, (fieldref_t)(void*)(ptr))
   
   static inline 
   c4snet_data_t* C4SNetAlloc(const struct io_cb* hnd, c4snet_type_t type, size_t size, void ∗∗data)
   {
       fieldref_t r = svp_new(hnd, size, type);
       svp_access(hnd, r, dataptr);
       return (c4snet_data_t*)(void*)r;
   }
   
   static inline
   size_t C4SNetSizeof(const struct io_cb* hnd, c4snet_data_t∗ ptr)
   {
       size_t v;
       svp_getmd(hnd, (fieldref_t)(void*)(ptr), &v, 0, 0);
       return v;
   }
   
   static inline
   void* C4SNetGetData(const struct io_cb* hnd, c4snet_data_t∗ ptr)
   {
       void *v;
       svp_access(hnd, (fieldref_t)(void*)(ptr), &v);
       return v;
   }

We list these "emulation" functions here for clarity and to illustrate
how the new API differs from the old. The main change compared to the
original C4SNet is that each API function learns "where" it was called
from from its 1st argument.

Field management for the environment
====================================

Control entities (eg synchrocells, management of flow inheritance) may
need to duplicate the reference, ie perform a "shallow copy".

Although we don't want box code to use the concept of "shallow copy"
because it is confusing, there are some instances in the RTS where it
makes sense to have it.

So the ``io_cb`` that a control entity will use is extended as follows:

.. code:: c

   struct io_cb_api {
      /* ... other APIs already mentioned above .. */
 
      // copyref: creates a new reference to the same object.
      fieldref_t (*copyref)(const struct io_cb*, fieldref_t r);
   }
   #define svp_copyref(x, y)     x->api->copyref(x, y)

After ``copyref`` is called, ``release`` must be called on both the
original and the copy. 

``copyref`` may return 0 to indicate an invalid reference was given as input.

Each control entity will have its own "clean up" list. However,
``copyref`` does not touch the "clean up" list. In
particular:

- if the input reference ``r1`` is already on the "clean up" list, and
  ``release`` is subsequently not used on ``r1``, then ``release``
  will be automatically called on ``r1`` after the control entity ends.
 
- however the result of ``copyref`` never goes on the "clean up" list 
  so it should be explicitly ``released`` somewhere:
 
  - either by the control entity itself, or

  - it arrives as input at a box entity A, in which case it is placed on
    the clean up list of A before A is activated.

Field database
==============

The field database is only visible from box/control entity code using
the ``io_cb`` API documented above. 

Another API will be described separately for monitoring/analysis code
which wants to tracks how many fields are currently allocated, who has
allocated what, and so on.

Concrete type database
======================

Like the field database, the concrete type database is invisible to
box/control entity code. However we give a few words here to clarify
what is its role and how it is possible to use language-specific data
type with the management API presented above.

The purpose of the concrete type database is to map ``typeid_t``
values to the type-specific object management APIs: allocate,
deallocate, serialize, deserialize, deepcopy.

The box code only sees and gives ``typeid_t`` to the field management
API documented above. The field management API, in turn, only stores
``typeid_t`` values alongside the objects in the field database.
Only for ``new``, ``clone``, ``release`` with refcount 1, the field
database then communicates with the concrete type database to
delegate the actual management of data.
So to give control of data to the field management database, each language
must *register* its object management API to the environment.

For this we provide the following API:

.. code:: c

   struct registrar {
      const struct reg_api *api;
      /* hidden fields here */
   };

   typedef ... langid_t;

   struct reg_api {
      langid_t (*reg_lang)(const struct registrar* reg, struct lang_cb* langmgr, const char *humanname);
      void     (*reg_type)(const struct registrar* reg, langid_t thelang, typeid_t thetype, const char *humanname);
   };

   #define svp_reg_lang(x, y, z)    x->api->reg_lang(x, y)
   #define svp_reg_type(w, x, y, z) x->api->reg_type(w, x, y, z)

   struct lang_cb {
     int     (*init)(void** langctx);
     void    (*cleanup)    (void* langctx);

     void*   (*allocate)   (void* langctx, typeid_t thetype, size_t thesize, size_t *realsize);
     void    (*deallocate) (void* langctx, typeid_t thetype, size_t thesize, void* data);
     void*   (*clone)      (void* langctx, typeid_t thetype, size_t thesize, void* data);

     size_t  (*getsersize) (void* langctx, typeid_t thetype, size_t objsize, const void *data);
     int     (*serialize)  (void* langctx, typeid_t thetype, size_t objsize, const void *data, char* dstbuf, size_t bufsize);

     size_t  (*getdesersize)(void* langctx, typeid_t thetype, const char* srcbuf, size_t bufsize);
     int     (*deserialize)(void* langctx, typeid_t thetype, const char* srcbuf, size_t bufsize, void **data, size_t *objsize);
   };
      
When a language run-time is started up, it can obtain a pointer to a
``struct registrar*``, which it can subsequently use to register
itself and its type management.

The function pointers ``init``, ``cleanup``, ``getdesersize`` are
optional. All other function pointers are mandatory.

For example:

.. code:: c

   void mylang_start_up(...., const struct registrar* reg)
   {
       struct lang_cb mycb = {
            NULL, NULL, /* no init() nor clean-up() for this language */
            &mylang_alloc,
            &mylang_dealloc,
            &mylang_clone,
            &mylang_getsersize,
            &mylang_serialize,
            NULL, /* no getdesersize() for this language */
            &mylang_deserialize
            };

       langid_t l = svp_reg_lang(reg, &mycb);        
       svp_reg_type(reg, l, 0, "myconcretetypeA");
       svp_reg_type(reg, l, 1, "myconcretetypeB");
       svp_reg_type(reg, l, 2, "myconcretetypeC");
    }

Predefined languages and types
------------------------------

The special ``langid_t`` with value 0 is the "common data language",
which is the data language used by all entities which are not configured to
use another data language.

In the common data language the following types are predefined:

- ``BYTES_UNALIGNED``: size unit is bytes, no alignment expected.

- ``BYTES_SCALAR_ALIGNED``: size unit is bytes, allocation is scalar
  aligned (aligned on uintmax_t or long long double, whichever is
  largest)

- ``BYTES_CACHE_ALIGNED``: size unit is bytes, allocation is scalar
  and cache line aligned.

- ``BYTES_PAGE_ALIGNED``: size unit is bytes, allocation page
  aligned.

All these types serialize and deserialize to themselves.

Intended semantics of the type management functions
---------------------------------------------------

- ``allocate``: allocate a new object of the specified type and size
  on the heap, return a pointer to it. Also update ``realsize`` with
  the size actually usable by the program. For example a program may
  require an allocation of 15 bytes and the minimum allocation size is
  32 bytes. Then ``realsize`` should be updated to 32.

- ``deallocate``: release a previously allocated object. The type and size
  are both indicated for reference, in case the deallocator uses separate
  heaps for different types/sizes.

- ``clone``: duplicate an object.

- ``getsersize``: get a conservative estimate of the buffer size
  needed for serialization.

- ``serialize``: serialize the data. The output buffer is
  pre-allocated.

- ``getdesersize``: get a conservative estimate of the object size
  needed for deserialization.

- ``deserialize``: deserialize the data. The ``deserialize`` function
  should reuse the provided ``data`` pointer to regenerate the object
  if it is not NULL and ``objsize`` is large enough; otherwise it
  should deallocate the provided ``data`` pointer and substitute it
  with a new allocation of the proper size. ``objsize`` should then be
  updated accordingly.

The environment guarantees it will call ``init`` after system
initialization is complete but before the application starts up. After
``init`` is called and if it returns 0, the environment will pass the
value of ``langctx`` updated by ``init`` to all the other APIs, so
that they can carry state around. If ``init`` returns non-zero, an error
will be reported and the application will not be allowed to use that
language interface.

The other APIs (alloc/dealloc/clone/ser/deser) should assume they may be
called concurrently and perform their own mutual exclusion if needed.

The environment will also call ``cleanup`` after the application
terminates but before the system shuts down.

If ``getdesersize`` is not provided, the environment will provide a
NULL ``data`` pointer to ``deserialize``, which should then thus
allocate a fresh object.

The reason why serialize/getsersize and deserialize/getdesersize are
decoupled is that the environment may select different instances of the
language-specific run-time system depending on where the data will be used.

Wrapping up
===========

Here is the code for ``langif.h``:

.. include:: ../inc/langif.h
   :code: c

Changes needed to existing application code
-------------------------------------------

The new ``svp_*`` macros should be used, or alternatively the existing
``C4SNet*`` calls should be adapted to provide the ``hnd`` as first
argument.

Also, the box code should be checked with regards to field ownership,
to ensure that fields are not released more than needed.

