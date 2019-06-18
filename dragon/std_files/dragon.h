#ifndef DRAGON_OBJECT_H
#define DRAGON_OBJECT_H

#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>

#define GET_META(obj) ((struct BaseObject*) obj->meta.self)

#define DRGN_INCREF(obj) (*(GET_META(obj)->ref_ptr))++

#define DRGN_DECREF(obj)  \
    do {  \
        int* ref_ptr = GET_META(obj)->ref_ptr;  \
        (*ref_ptr)--;  \
        if ((*ref_ptr) <= 0) {  \
             GET_META(obj)->del(obj->meta.self);  \
        }  \
    } while(0)


// struct Linked {
//     struct BaseObject* obj;
//     struct Linked* next;
// }


struct BaseObject {
    void* self;
    void* up;

    int ref_count;              // only changed on self
    void (*del)(void*);
    int* ref_ptr;
    // struct Linked* linked;  // only available on self
};


struct Object {
    struct BaseObject meta;

    struct String* (*to_string)(void*);
};


struct String {
    struct BaseObject meta;

    struct Object parent_Object;

    char* str;
    int len;
};


struct Integer {
    struct BaseObject meta;

    struct Object parent_Object;

    int num;
};


bool is_null(struct Object*);


void new_parent_Object(struct Object*, void*, void*);
struct String* Object_to_string(void*);


struct String* _new_String(char*, int);
struct String* new_String(void*);
struct String* String_to_string(void*);


struct Integer* _new_Integer(int);
void new_parent_Integer(struct Integer*, void*, void*);
struct String* Integer_to_string(void*);


void print(struct Object*);

int dragon_clock();

#endif