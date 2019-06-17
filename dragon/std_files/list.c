#include <stdlib.h>
#include <stdio.h>
#include "dragon.h"
#include "list.h"


struct _Array;


struct _Array* new__Array(int size) {
    void* mem = calloc(size, sizeof(struct Object**));
    struct _Array* arr = malloc(sizeof(struct _Array));
    arr->meta.self = arr;
    arr->meta.up = arr;

    arr->length = size;
    arr->items = mem;

    arr->get_item = _Array_get_item;
    arr->set_item = _Array_set_item;

    new_parent_Object((&arr->parent_Object), arr, arr);

    return arr;
}


struct Object* _Array_get_item(struct _Array* array, int index) {
    if (index >= array->length) {
        printf("Cannot get index %i: out of range (length %i)\n", index, array->length);
        return NULL;
    }
    return array->items[index];
}


void _Array_set_item(struct _Array* array, int index, struct Object* val) {
    if (index >= array->length) {
        printf("Cannot set index %i: out of range (length %i)\n", index, array->length);
    }
    array->items[index] = val;
}

