#ifndef LIST_H
#define LIST_H


// DRAGON: {"class":
// {"class":


struct _Array {
    void* self;
    void* up;

    struct Object parent_Object;

    int length;
    struct Object** items;

    struct Object* (*get_item)(struct _Array*, int);
    void (*set_item)(struct _Array*, int, struct Object*);
};

struct _Array* new__Array(int);

struct Object* _Array_get_item(struct _Array*, int);
void _Array_set_item(struct _Array*, int, struct Object*);

#endif
