#ifndef LIST_H
#define LIST_H


// DRAGON: {"class":
// {"class":


struct Array {
    void* self;
    void* up;
    int length;
    struct Object* items;
};

struct Array* new_array(int);

struct Object* array_get_item(struct Array*, int);

#endif
