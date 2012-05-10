#ifndef BOXIF_H
#define BOXIF_H


/* proposed logging levels */
#define  LOG_NOTSET   0
#define  LOG_DEBUG    10   /* printf-style debugging */
#define  LOG_INFO     20   /* what is being communicated, identifiers, etc. */
#define  LOG_WARN     30   /* unexpected conditions, can resume */
#define  LOG_ERROR    40   /* unexpected condition, will terminate computation prematurely */
#define  LOG_FATAL    50   /* unexpected condition, behavior undefined */

/* we use "unsigned long" here although we might use a larger/smaller
   type in a different implementation. */
typedef uintptr_t fieldref_t;

/* we use "unsigned long" here although we might use a larger/smaller
   type in a different implementation. */
typedef uintptr_t typeid_t;


/* the "io_cb" structure used by box/control entities. */

struct io_cb {
    const struct io_cb_api *api;
    /* invisible additional fields here
       to identify the calling task, its private state, etc. */
};

struct io_cb_api {
    /* general output functions */
    int   (*out)(const struct io_cb*, ...);
    void  (*log)(const struct io_cb*, int loglevel, const char *fmt, ...);
   
    /* field management functions fox box/control entities */
    fieldref_t (*new)    (const struct io_cb*, size_t thesize, typeid_t thetype);
    void       (*release)(const struct io_cb*, fieldref_t theref);
    int        (*access) (const struct io_cb*, fieldref_t theref, void **ptr)
    int        (*getmd)  (const struct io_cb*, fieldref_t theref, size_t *thesize, typeid_t *thetype, size_t *realsize);
    fieldref_t (*clone)  (const struct io_cb*, fieldref_t theref);
    fieldref_t (*wrap)   (const struct io_cb*, typeid_t thetype, size_t thesize, void* data);
    int        (*resize) (const struct io_cb*, fieldref_t theref, size_t newsize);
 
    /* field management functions for control entities only */
    fieldref_t (*copyref)(const struct io_cb*, fieldref_t r);
};

/* wrapper macros to simplify usage of the above */

#define svp_out(x, ...)       x->api->out(x, __VA_ARGS__)
#define svp_log(x, y, z, ...) x->api->log(x, y, z, __VA_ARGS__)
#define svp_release(x, y)     x->api->release(x, y)
#define svp_access(x, y, z)   x->api->access(x, y, z)
#define svp_getmd(w, x, y, z) x->api->getmd(w, x, y, z)
#define svp_clone(x, y)       x->api->clone(x, y)
#define svp_wrap(w, x, y, z)  x->api->wrap(w, x, y, z)
#define svp_resize(x, y, z)   x->api->resize(x, y, z)
#define svp_copyref(x, y)     x->api->copyref(x, y)

/*** optional backward compatibility with C4SNet ***/

typedef struct {/*unneeded*/} c4snet_data_t;

#define C4SNetOut svp_out

/* for the following, we achieve partial backward compatibility only:
 * we need the hnd as first argument for all the functions. */

#define C4SNetCreate(hnd, type, size, data) \
    ((c4snet_data_t*)(void*)svp_wrap(hnd, type, size, data))

#define C4SNetFree(hnd, ptr) \
    svp_release(hnd, (fieldref_t)(void*)(ptr))

static inline 
c4snet_data_t* C4SNetAlloc(const struct io_cb* hnd, c4snet_type_t type, size_t size, void **data)
{
    fieldref_t r = svp_new(hnd, size, type);
    svp_access(hnd, r, dataptr);
    return (c4snet_data_t*)(void*)r;
}

static inline
size_t C4SNetSizeof(const struct io_cb* hnd, c4snet_data_t* ptr)
{
    size_t v;
    svp_getmd(hnd, (fieldref_t)(void*)(ptr), &v, 0, 0);
    return v;
}

static inline
void* C4SNetGetData(const struct io_cb* hnd, c4snet_data_t* ptr)
{
    void *v;
    svp_access(hnd, (fieldref_t)(void*)(ptr), &v);
    return v;
}
        

#endif
