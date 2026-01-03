#include <neweng/engine.h>
#include <stdio.h>

typedef struct {
    void *data;
    bool is_freeless;
    NEnt_intf intf;
} Ent__Data;

Ent__Data *ent_arr = NULL;
size_t ent_count = 0, ent_cap = 0;

static NEnt_ent ent_current = -1;

NEnt_ent NEnt_add(NEnt_intf intf) {
    size_t pos = 0;
    
    if (!ent_arr) {
        ent_cap = 1024;
        ent_count = 0;
        ent_arr = malloc(sizeof(Ent__Data)*ent_cap);
    }
    if (ent_count + 1 >= ent_cap) {
        for (size_t i = 0; i < ent_count; ++i) {
            if (!ent_arr[i].is_freeless) {
                pos = i;
                goto append;
            }
        }
        ent_cap <<= 1;
        ent_arr = realloc(ent_arr, sizeof(Ent__Data)*ent_cap);
    }
    pos = ent_count++;
  append:
    ent_arr[pos].data = intf.alloc(pos);
    ent_arr[pos].is_freeless = true;
    ent_arr[pos].intf = intf;
    return pos;
}

void NEnt_destroy(NEnt_ent id) {
    if (id < 0 || id > ent_count) return;
    ent_arr[id].is_freeless = false;
}

s32 NEnt_get_intfid(NEnt_ent ent) {
    if (ent < 0 || ent > ent_count || !ent_arr[ent].is_freeless) return -1;
    return ent_arr[ent].intf.intf_id;
}

void NEnt_update(void) {
    if (ent_current != -1) return; // Entities shouldn't call update loop
    bool isFixed = ((s32)(NE_deltaTime*10.)) % 3 == 0;
    for (size_t i = 0; i < ent_count; ++i) {
        if (ent_arr[i].is_freeless) {
            ent_current = i;
            ent_arr[i].intf.onmsg(ent_arr[i].data, i, -1, NENT_MSG_UPDATE, NULL);
            if (isFixed) {
                ent_arr[i].intf.onmsg(ent_arr[i].data, i, -1, NENT_MSG_30Hz_UPDATE, NULL);
            }
            ent_arr[i].intf.onmsg(ent_arr[i].data, i, -1, NENT_MSG_RENDER, NULL);
        }
    }
    ent_current = -1;
}

void NEnt_send(NEnt_Msg_Kind msg_kind, NEnt_ent callee, void *msg_data) {
    if (callee < 0 || callee > ent_count || !ent_arr[callee].is_freeless) return;
    NEnt_ent caller = ent_current;
    ent_current = callee;
    ent_arr[callee].intf.onmsg(ent_arr[callee].data, callee, caller, msg_kind, msg_data);
    ent_current = caller;
}

