#pragma once
#include <neweng/main.h>

typedef s32 NEnt_ent;

// ent -1 is reserved for the engine.

typedef enum {
    NENT_MSG_UPDATE,
    NENT_MSG_RENDER,
    NENT_MSG_30Hz_UPDATE,
    NENT_MSG_USR1,
    NENT_MSG_USR2
} NEnt_Msg_Kind;

typedef struct {
    void *(*alloc)(NEnt_ent id);
    void(*dealloc)(void *ent, NEnt_ent id);
    void(*onmsg)(void *ent, NEnt_ent id, NEnt_ent caller, NEnt_Msg_Kind msg_kind, void *msg);
} NEnt_intf;

NEnt_ent NEnt_add(NEnt_intf intf);
void NEnt_update(void);
void NEnt_send(NEnt_Msg_Kind msg_kind, NEnt_ent callee, void *msg_data);
