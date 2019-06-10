#ifndef TEST_H
#define TEST_H
#include "stdio.h"

#include "stdlib.h"

#include "dragon.h"

#include "list.h"

struct Person_0;


struct Person_0* new_empty_Person_0();

void new_parent_Person_0(struct Person_0* , void* , void* );

struct String* Person_0_redirect_to_string_5(void* );

void say_hi_4(void* , char* );

struct Person_0* new_Person_0();

struct RealPerson_1;


struct RealPerson_1* new_empty_RealPerson_1();

void new_parent_RealPerson_1(struct RealPerson_1* , void* , void* );

void RealPerson_1_redirect_say_hi_7(void* , char* );

struct String* RealPerson_1_redirect_to_string_8(void* );

struct RealPerson_1* new_RealPerson_1();

struct Holder_2;


struct Holder_2* new_empty_Holder_2();

void new_parent_Holder_2(struct Holder_2* , void* , void* );

struct String* Holder_2_redirect_to_string_9(void* );

struct Holder_2* new_Holder_2();

int main_3();

int main();

#endif  // TEST_H