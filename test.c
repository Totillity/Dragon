#include "test.h"

#include "stdio.h"

#include "stdlib.h"

#include "dragon.h"

#include "list.h"

struct Person_0 {
    void* self;
    void* up;
    struct Object parent_Object;
    char* name;
    int age;
    void (*say_hi)(void*, char*);
};


struct Person_0* new_empty_Person_0() {
    struct Person_0* obj = malloc(sizeof(struct Person_0));
    obj->self = obj;
    obj->up = obj;
    new_parent_Object((&obj->parent_Object), obj, obj);
    (*obj).name = "";
    (*obj).age = 0;
    (*obj).say_hi = say_hi_4;
    (*obj).parent_Object.to_string = Person_0_redirect_to_string_5;
    return obj;
}


void new_parent_Person_0(struct Person_0* parent_ptr, void* child_ptr, void* self_ptr) {
    parent_ptr->self = self_ptr;
    parent_ptr->up = child_ptr;
    (&new_parent_Object)((&parent_ptr->parent_Object), parent_ptr, self_ptr);
}


struct String* Person_0_redirect_to_string_5(void* _self) {
    struct Person_0* self = _self;
    return Object_to_string((&(*self).parent_Object));
}


void say_hi_4(void* _self, char* to_6) {
    struct Person_0* self = ((struct Person_0*) _self);
    print((&(*_new_String("Hi, ")).parent_Object));
    print((&(*_new_String(to_6)).parent_Object));
    print((&(*_new_String(", I'm ")).parent_Object));
    print((&(*_new_String((*self).name)).parent_Object));
    print((&(*_new_String("\n")).parent_Object));
}


struct Person_0* new_Person_0() {
    struct Person_0* obj = new_empty_Person_0();
    return obj;
}


struct RealPerson_1 {
    void* self;
    void* up;
    struct Person_0 parent_Person_0;
};


struct RealPerson_1* new_empty_RealPerson_1() {
    struct RealPerson_1* obj = malloc(sizeof(struct RealPerson_1));
    obj->self = obj;
    obj->up = obj;
    new_parent_Person_0((&obj->parent_Person_0), obj, obj);
    (*obj).parent_Person_0.name = "";
    (*obj).parent_Person_0.age = 0;
    (*obj).parent_Person_0.say_hi = RealPerson_1_redirect_say_hi_7;
    (*obj).parent_Person_0.parent_Object.to_string = RealPerson_1_redirect_to_string_8;
    return obj;
}


void new_parent_RealPerson_1(struct RealPerson_1* parent_ptr, void* child_ptr, void* self_ptr) {
    parent_ptr->self = self_ptr;
    parent_ptr->up = child_ptr;
    (&new_parent_Person_0)((&parent_ptr->parent_Person_0), parent_ptr, self_ptr);
}


void RealPerson_1_redirect_say_hi_7(void* _self, char* arg_0) {
    struct RealPerson_1* self = _self;
    say_hi_4((&(*self).parent_Person_0), arg_0);
}


struct String* RealPerson_1_redirect_to_string_8(void* _self) {
    struct RealPerson_1* self = _self;
    return Object_to_string((&(*self).parent_Person_0.parent_Object));
}


struct RealPerson_1* new_RealPerson_1() {
    struct RealPerson_1* obj = new_empty_RealPerson_1();
    return obj;
}


struct Holder_2 {
    void* self;
    void* up;
    struct Object parent_Object;
    struct Person_0* person;
};


struct Holder_2* new_empty_Holder_2() {
    struct Holder_2* obj = malloc(sizeof(struct Holder_2));
    obj->self = obj;
    obj->up = obj;
    new_parent_Object((&obj->parent_Object), obj, obj);
    (*obj).person = NULL;
    (*obj).parent_Object.to_string = Holder_2_redirect_to_string_9;
    return obj;
}


void new_parent_Holder_2(struct Holder_2* parent_ptr, void* child_ptr, void* self_ptr) {
    parent_ptr->self = self_ptr;
    parent_ptr->up = child_ptr;
    (&new_parent_Object)((&parent_ptr->parent_Object), parent_ptr, self_ptr);
}


struct String* Holder_2_redirect_to_string_9(void* _self) {
    struct Holder_2* self = _self;
    return Object_to_string((&(*self).parent_Object));
}


struct Holder_2* new_Holder_2() {
    struct Holder_2* obj = new_empty_Holder_2();
    return obj;
}


int main_3() {
    struct Holder_2* holder_10 = new_Holder_2();
    struct RealPerson_1* bob_11 = new_RealPerson_1();
    (*bob_11).parent_Person_0.name = "Bob";
    (*bob_11).parent_Person_0.age = 7;
    (*bob_11).parent_Person_0.say_hi(bob_11->self, "Jane");
    (*holder_10).person = (&(*bob_11).parent_Person_0);
    (*(*holder_10).person).say_hi((*holder_10).person->self, "Jane");
    return 0;
}


int main() {
    return main_3();
}


