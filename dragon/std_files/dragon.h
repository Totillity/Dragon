#ifndef DRAGON_OBJECT_H
#define DRAGON_OBJECT_H

#include <stdbool.h>
#include <stdlib.h>

struct BaseObject {
    void* self;
    void* up;
};


struct Object {
    void* self;
    void* up;

    struct String* (*to_string)(void*);
};


struct String {
    void* self;
    void* up;

    struct Object parent_Object;

    char* str;
    int len;
};


struct Integer {
    void* self;
    void* up;

    struct Object parent_Object;

    int num;
};


bool is_null(struct Object*);


void new_parent_Object(struct Object*, void*, void*);
struct String* Object_to_string(void*);


struct String* _new_String(char*);
struct String* new_String(void*);
struct String* String_to_string(void*);


struct Integer* _new_Integer(int);
void new_parent_Integer(struct Integer*, void*, void*);
struct String* Integer_to_string(void*);


void print(struct Object*);
void print_str(char*);
void print_int(int);

int dragon_clock();

#endif