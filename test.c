#include "test.h"

#include "stdio.h"

#include "stdlib.h"

#include "/Users/MagilanS/PycharmProjects/Dragon2/dragon/c_files/dragon.h"

#include "/Users/MagilanS/PycharmProjects/Dragon2/dragon/c_files/list.h"

int fibo_0(int n_3) {
    if (n_3 < 2) 
        return n_3;
    else 
        return fibo_0(n_3 - 1) + fibo_0(n_3 - 2);
}


struct Dude_1 {
    void* self;
    void* up;
    struct Object parent_Object;
};


struct Dude_1* new_empty_Dude_1() {
    struct Dude_1* obj = malloc(sizeof(struct Dude_1));
    obj->self = obj;
    obj->up = obj;
    new_parent_Object((&obj->parent_Object), obj, obj);
    (*obj).parent_Object.to_string = Dude_1_redirect_to_string_4;
    return obj;
}


void new_parent_Dude_1(struct Dude_1* parent_ptr, void* child_ptr, void* self_ptr) {
    parent_ptr->self = self_ptr;
    parent_ptr->up = child_ptr;
    (&new_parent_Object)((&parent_ptr->parent_Object), parent_ptr, self_ptr);
}


struct String* Dude_1_redirect_to_string_4(void* _self) {
    struct Dude_1* self = _self;
    return Object_to_string((&(*self).parent_Object));
}


struct Dude_1* new_Dude_1() {
    struct Dude_1* obj = new_empty_Dude_1();
    return obj;
}


int main_2() {
    int start_5 = dragon_clock();
    print((&(*_new_Integer(fibo_0(35))).parent_Object));
    int end_6 = dragon_clock();
    print((&(*_new_Integer(end_6 - start_5)).parent_Object));
    return 0;
}


int main() {
    return main_2();
}


