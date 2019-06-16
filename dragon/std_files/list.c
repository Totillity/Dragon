#include <stdlib.h>
#include "dragon.h"
#include "list.h"


struct _Array;


struct _Array* new__array(int size) {
    void* mem = calloc(size, sizeof(struct Object*));
    struct _Array* arr = malloc(sizeof(struct _Array));
    arr->self = arr;
    arr->up = arr;
    arr->length = size;
    arr->items = mem;
    return arr;
}


struct Object* _array_get_item(struct _Array* array, int index) {
    return &array->items[index];
}
