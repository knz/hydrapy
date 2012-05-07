#ifndef BOXIF_H
#define BOXIF_H


// proposed logging levels
#define  LOG_NOTSET   0
#define  LOG_DEBUG    10   // printf-style debugging
#define  LOG_INFO     20   // what is being communicated, identifiers, etc
#define  LOG_WARN     30   // unexpected conditions, can resume
#define  LOG_ERROR    40   // unexpected condition, will terminate computation prematurely
#define  LOG_FATAL    50   // unexpected condition, behavior undefined

// we use "unsigned long" here although we might
// use a larger/smaller type in a different implementation.
typedef unsigned long fieldref_t;

// we use "unsigned long" here although we might
// use a larger/smaller type in a different implementation.
typedef unsigned long typeid_t;



// the "io_cb" API table used by box/control entities.


struct io_cb {
    /* general out functions */
    int   (*out)(struct io_cb*, ...);
    void  (*log)(struct io_cb*, int loglevel, const char *fmt, ...);
   
    /* field management functions fox box/control entities */
    fieldref_t (*new)    (struct io_cb*, size_t thesize, typeid_t thetype);
    void       (*release)(struct io_cb*, fieldref_t theref);
    int        (*access) (struct io_cb*, fieldref_t theref, void **ptr)
    int        (*getmd)  (struct io_cb*, fieldref_t theref, size_t *thesize, typeid_t *thetype, size_t *realsize);
    fieldref_t (*clone)  (struct io_cb*, fieldref_t theref);
    fieldref_t (*wrap)   (struct io_cb*, typeid_t thetype, void* data);
    int        (*resize) (struct io_cb*, fieldref_t theref, size_t newsize);
 
    /* field management functions for control entities only */
    fieldref_t (*copyref)(struct io_cb*, fieldref_t r);
};

/* optional backward compatibility */
#define C4SNetOut(hnd, ...) \
    (((struct cb_io*)hnd)->out((struct cb_io*)hnd, __VA_ARGS__)

#endif
