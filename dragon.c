#include "dragon.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct Object;

struct String;

struct Integer;


struct String* Object_to_string(void* _self) {
    struct Object* self = _self;
    char buffer[100];

    int len = snprintf(buffer, 100, "%p", self);
    char* chars = calloc(len+1, sizeof(char));
    chars[len] = '\0';
    strncpy(chars, buffer, len+1);
    return _new_String(chars);
}


void new_parent_Object(struct Object* parent_ptr, void* child_ptr, void* self_ptr) {
    parent_ptr->self = self_ptr;
    parent_ptr->up = child_ptr;
}


struct String* _new_String(char* chars) {
    struct String* obj = malloc(sizeof(struct String));

    (*obj).str = chars;
    (*obj).len = strlen(chars);

    obj->self = obj;
    obj->up = obj;

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
    parent_ptr->self = self_ptr;
    parent_ptr->up = child_ptr;
}


struct Integer* _new_Integer(int num) {
    struct Integer* obj = malloc(sizeof(struct Integer));
    obj->num = num;

    obj->self = obj;
    obj->up = obj;

    new_parent_Object((&obj->parent_Object), obj, obj);

    obj->parent_Object.to_string = Integer_to_string;

    return obj;
}


struct String* Integer_to_string(void* _self) {
    struct Integer* self = _self;

    char buffer[100];

    int len = snprintf(buffer, 100, "%i", self->num);
    char* chars = calloc(len+1, sizeof(char));
    chars[len] = '\0';
    strncpy(chars, buffer, len+1);
    return _new_String(chars);
}

// struct Integer* new_Integer(void* _obj) {
//
// }


void print(struct Object* _obj) {
    struct String* str = _obj->to_string(_obj->self);

    // puts(str->str);
    printf("%s", str->str);
}


void print_str(char* obj) {
    printf("%s", obj);
}

void print_int(int obj) {
    printf("%i", obj);
}
