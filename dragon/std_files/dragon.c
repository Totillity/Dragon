#include "dragon.h"
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <time.h>

struct BaseObject;

struct Object;

struct String;

struct Integer;


void* drgn_inc_ref(void* obj) {
    (*((struct BaseObject*) ((struct BaseObject*) obj)->self)->ref_ptr)++;
    return obj;
}


bool is_null(struct Object* obj) {
    return obj->meta.self == NULL;
}


struct String* Object_to_string(void* _self) {
    struct Object* self = _self;
    char buffer[100];

    int len = snprintf(buffer, 100, "%p", self);
    return _new_String(buffer, len);
}


void new_parent_Object(struct Object* parent_ptr, void* child_ptr, void* self_ptr) {
    parent_ptr->meta.self = self_ptr;
    parent_ptr->meta.up = child_ptr;
}


void del_String(void* obj) {
    struct String* str = obj;
    // printf("Freeing str %s\n", str->str);
    free(str->str);
    free(str);
}


struct String* _new_String(char* chars, int len) {
    struct String* obj = malloc(sizeof(struct String));

    (*obj).str = memcpy(calloc(len, sizeof(char)), chars, len);
    (*obj).len = len;

    obj->meta.self = obj;
    obj->meta.up = obj;
    obj->meta.ref_count = 0;
    obj->meta.ref_ptr = &(obj->meta.ref_count);
    obj->meta.del = del_String;

    new_parent_Object((&obj->parent_Object), obj, obj);

    obj->parent_Object.to_string = String_to_string;

    return obj;
}

struct String* new_String(void* _obj) {
    struct Object* obj = _obj;
    struct String* str = (*obj).to_string(obj);
    return str;
}


struct String* String_to_string(void* _self) {
    struct String* self = _self;
    return self;
}


void new_parent_Integer(struct Integer* parent_ptr, void* child_ptr, void* self_ptr) {
    parent_ptr->meta.self = self_ptr;
    parent_ptr->meta.up = child_ptr;
}


void del_Integer(void* obj) {
    struct Integer* num = obj;
    free(num);
}


struct Integer* _new_Integer(int num) {
    struct Integer* obj = malloc(sizeof(struct Integer));
    obj->num = num;

    obj->meta.self = obj;
    obj->meta.up = obj;

    obj->meta.ref_count = 0;
    obj->meta.ref_ptr = &(obj->meta.ref_count);
    obj->meta.del = del_Integer;

    new_parent_Object((&obj->parent_Object), obj, obj);

    obj->parent_Object.to_string = Integer_to_string;

    return obj;
}


struct String* Integer_to_string(void* _self) {
    struct Integer* self = _self;
    char buffer[100];

    int len = snprintf(buffer, 100, "%i", self->num);
    return _new_String(buffer, len);
}

// struct Integer* new_Integer(void* _obj) {
//
// }


void print(struct Object* _obj) {
    DRGN_INCREF(_obj);
    struct String* str = _obj->to_string(_obj->meta.self);

    for (int i = 0; i < str->len; i++) {
        putchar(str->str[i]);
    }
    fflush(stdout);
    DRGN_DECREF(_obj);
}


int dragon_clock() {
    return clock() * 1000 / CLOCKS_PER_SEC;
}
