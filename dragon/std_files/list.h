#ifndef LIST_H
#define LIST_H


// DRAGON: {"class":
// {"class":


struct _Array {
    void* self;
    void* up;
    int length;
    struct Object* items;
};

struct _Array* new__array(int);

struct Object* _array_get_item(struct _Array*, int);

#endif
