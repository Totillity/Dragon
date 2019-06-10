#include <stdlib.h>
#include "dragon.h"
#include "list.h"


struct Array;


struct Array* new_array(int size) {
    void* mem = calloc(size, sizeof(struct Object*));
    struct Array* arr = malloc(sizeof(struct Array));
    arr->self = arr;
    arr->up = arr;
    arr->length = size;
    arr->items = mem;
    return arr;
}


struct Object* array_get_item(struct Array* array, int index) {
    return &array->items[index];
}
