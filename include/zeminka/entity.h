#pragma once
#include <zeminka/main.h>

typedef s32 ZEEnt_ent;

// ent -1 is reserved for the engine.

typedef enum {
    ZEENT_MSG_UPDATE,
    ZEENT_MSG_RENDER,
    ZEENT_MSG_30Hz_UPDATE,
    ZEENT_MSG_USR1,
    ZEENT_MSG_USR2
} ZEEnt_Msg_Kind;

typedef struct {
    void *(*alloc)(ZEEnt_ent id);
    void(*dealloc)(void *ent, ZEEnt_ent id);
    void(*onmsg)(void *ent, ZEEnt_ent id, ZEEnt_ent caller, ZEEnt_Msg_Kind msg_kind, void *msg);
    s32 intf_id;
} ZEEnt_intf;

ZEEnt_ent ZEEnt_add(ZEEnt_intf intf);
void ZEEnt_update(void);
void ZEEnt_destroy(ZEEnt_ent id);
s32 ZEEnt_get_intfid(ZEEnt_ent ent); // -1 - no such entity
void ZEEnt_send(ZEEnt_Msg_Kind msg_kind, ZEEnt_ent callee, void *msg_data); // doesn't need caller id
