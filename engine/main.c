#include <neweng/engine.h>

#include <stdlib.h>
#include <stdio.h>

#ifdef _WIN32
#include <windows.h>
#endif

static double getSystemTime() { // TODO: public functions
#if defined(_WIN32)
    FILETIME system_time;
    ULARGE_INTEGER large;

    GetSystemTimePreciseAsFileTime(&system_time);
    large.u.LowPart = system_time.dwLowDateTime;
    large.u.HighPart = system_time.dwHighDateTime;
    const u64 scale_factor = 1000000;
    u64 q = large.QuadPart/10;
    return (f64)q/(f64)scale_factor;
#elif defined(__APPLE__)
    natodo("Apple MacOSX");
#else
#include <time.h> // Stolen from RGFW and rewrotten with floats.
    struct timespec ts;
    const u64 scale_factor = 1000000000;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (f64)ts.tv_sec + (f64)ts.tv_nsec / (f64)scale_factor;
#endif
}

static double getDeltaTime() {
    static double latest = 0;
    double platest = latest;
    latest = getSystemTime();
    if (latest == 0)
        return 0;
    return latest-platest;
}

#define INTF_BBALL 0
#define INTF_PLAYER 1

f64 NE_deltaTime = 0, NE_systemTime = 0;

typedef struct {
    NE_Vec2 pos, vel;
} BBall_Data;

static void *bball_alloc(NEnt_ent id) {
    BBall_Data *d = malloc(sizeof(BBall_Data));
    d->pos = NE_Vec2_From2(.1, .2);
    d->vel = NE_Vec2_From2(.3, .1);
    return d;
}

static void bball_onmsg(void *_ent, NEnt_ent ent_id, NEnt_ent caller, NEnt_Msg_Kind msg_kind, void *msg_data) {
    BBall_Data *ent = _ent;
    switch (msg_kind) {
    case NENT_MSG_UPDATE: {
        // MB i'll put something here.
    } break;
    case NENT_MSG_RENDER: {
        NScreen_DrawCircle(NE_Vec3_From3(ent->pos.x, ent->pos.y, 4.-4.*sqrt(ent->pos.x*ent->pos.x+ent->pos.y*ent->pos.y)), .01, NE_RED);
    } break;
    case NENT_MSG_30Hz_UPDATE: {
        ent->pos = NE_Vec2_Add(ent->pos, NE_Vec2_Scale(ent->vel, NE_deltaTime));
        const static double bs = .5f;
        if (ent->pos.x < -bs) {ent->pos.x = -bs;ent->vel.x *= -1;}
        if (ent->pos.x > bs) {ent->pos.x = bs;ent->vel.x *= -1;}
        if (ent->pos.y < -bs) {ent->pos.y = -bs;ent->vel.y *= -1;}
        if (ent->pos.y > bs) {ent->pos.y = bs;ent->vel.y *= -1;}
    } break;
    case NENT_MSG_USR1: {
        memcpy(&ent->pos, msg_data, sizeof(ent->pos));
    } break;
    default: {
        natodo("WTF just now is happened???");
    } break;
    }
}

static void bball_dealloc(void *ent, NEnt_ent id) {
    free(ent);
}

NEnt_intf bball_intf = {
    bball_alloc,
    bball_dealloc,
    bball_onmsg,
    INTF_BBALL
};

static const NE_Vertex player_model_v[] = {
    {-1, -1, -1},
    {-1, -1, +1},
    {-1, +1, +1},
    {-1, +1, -1},
    {+1, -1, -1},
    {+1, -1, +1},
    {+1, +1, +1},
    {+1, +1, -1}
};

static const NE_Color player_model_c[] = {
    NE_RED,
    NE_MAGENTA,
    NE_GREEN,
    NE_CYAN,
    NE_BLUE,
    NE_BLACK,
    NE_WHITE,
    NE_ORANGE,
};

static const NE_Face player_model_f[] = {   
    {0, 1, 2},
    {2, 3, 0},
    
    {0, 3, 4},
    {4, 7, 3},
    
    {3, 7, 6},
    {6, 2, 3},

    
    {0+4, 1+4, 2+4},
    {2+4, 3+4, 0+4},

    
    {0+1, 3-1, 4+1},
    {4+1, 7-1, 3-1},
    
    {3-3, 7-3, 6-1},
    {6-1, 2-1, 3-3},
};

static const NE_Model player_model = {
    player_model_v,
    player_model_c,
    player_model_f,
    12 // 6 rectangles and every rectangle is 2 triangle
};

typedef struct {
    NE_Vec3 pos, vel;
} Player_Data;

static void *player_alloc(NEnt_ent id) {
    Player_Data *d = malloc(sizeof(Player_Data));
    d->pos = NE_Vec3_From3(0,0,1.);
    d->vel = NE_Vec3_From3(0,0,0);
    return d;
}

static void player_onmsg(void *_ent, NEnt_ent ent_id, NEnt_ent caller, NEnt_Msg_Kind msg_kind, void *msg_data) {
    Player_Data *ent = _ent;
    switch (msg_kind) {
    case NENT_MSG_UPDATE: {
        if (ent->pos.y <= -5) NEnt_destroy(ent_id);
    } break;
    case NENT_MSG_RENDER: {
        // NScreen_DrawCircle(ent->pos, .01, NE_MYCOLOR);
        NE_TransformW tw = NE_Transform_Cache((NE_Transform) {
                ent->pos,
                {0,NE_systemTime,0},
                NE_Vec3_From1(.1),
            });
        NScreen_RenderModel(player_model, tw);
    } break;
    case NENT_MSG_30Hz_UPDATE: {
        ent->pos = NE_Vec3_Add(ent->pos, NE_Vec3_Scale(ent->vel, NE_deltaTime));
        ent->vel.y -= GRAV*NE_deltaTime;
        ent->vel = NE_Vec3_Add(ent->vel, NE_Vec3_Scale(ent->vel, NE_deltaTime*(.997-1.)));
        if (ent->pos.y < -2.1) {
            ent->vel.y *= -1;
            ent->vel.x *= .8;
            ent->vel.z *= .8;
            
            ent->pos.y = -2.1;
        }
        for (NEnt_ent id = 0;;++id) {
            if (id == ent_id) continue;
            s32 iid = NEnt_get_intfid(id);
            if (iid == -1) break;
            if (iid == INTF_PLAYER) { // TODO: i don't know to find collisions between two rotated cubes.
                Player_Data other_ent;
                NEnt_send(NENT_MSG_USR2, id, &other_ent);
                if (NE_Vec3_MagSq(NE_Vec3_Sub(ent->pos, other_ent.pos)) <= .1*.1+.1*.1+.1*.1) {
                    const float m1 = 1, m2 = 1;
                    NE_Vec3 v1 = ent->vel, v2 = other_ent.vel;
                    NE_Vec3 p1 = ent->pos, p2 = other_ent.pos;
                    NE_Vec3 v1d, v2d;
                    if (m1 < m2) {
                        NE_Vec3 d = NE_Vec3_Sub(p2, p1);
                        NE_Vec3 dn = NE_Vec3_Norm(d);
                        f64 k = DOT3(dn.x,dn.y,dn.z,v1.x,v1.y,v1.z);
                        v1d = NE_Vec3_Add(v1, NE_Vec3_Scale(d, 1+k));
                        v2d.x = NPhysics_cmsolver(m2, v2.x, m1, v1.x, v1d.x);
                        v2d.y = NPhysics_cmsolver(m2, v2.y, m1, v1.y, v1d.y);
                        v2d.z = NPhysics_cmsolver(m2, v2.z, m1, v1.z, v1d.z);
                    }
                    else {
                        v2d = NE_Vec3_Add(v2, NE_Vec3_Sub(p1, p2));
                        v1d.x = NPhysics_cmsolver(m1, v1.x, m2, v2.x, v2d.x);
                        v1d.y = NPhysics_cmsolver(m1, v1.y, m2, v2.y, v2d.y);
                        v1d.z = NPhysics_cmsolver(m1, v1.z, m2, v2.z, v2d.z);
                    }
                    ent->vel = v1d;
                    other_ent.vel = v2d;
                    NEnt_send(NENT_MSG_USR1, iid, &other_ent);
                }
            }
        }
        // ent->pos = NE_Vec3_From3(cos(NE_systemTime),.5*sin(2*NE_systemTime), 1.);
    } break;
    case NENT_MSG_USR1: {
        memcpy(ent, msg_data, sizeof(*ent));
    } break;
    case NENT_MSG_USR2: {
        memcpy(msg_data, ent, sizeof(*ent));
    } break;
    default: {
        natodo("WTF just now is happened???");
    } break;
    }
}

static void player_dealloc(void *ent, NEnt_ent id) {
    free(ent);
}

NEnt_intf player_intf = {
    player_alloc,
    player_dealloc,
    player_onmsg,
    INTF_PLAYER
};

f64 NE_mousedX = 0, NE_mousedY = 0;

int main() {
    NScreen_init(1280, 720, 120., "New Engine");

    NE_Vec3 pos = NE_Vec3_From3(0, 0, 1.);
    
    NEnt_add(bball_intf);
    
    NEnt_add(player_intf);
    
    f64 c_yaw = 0;
    f64 c_pitch = 0;
    NE_Vec3 c_pos = {0};
    
    while (NScreen_IsNtClosed()) {
        NE_deltaTime = getDeltaTime();
        NE_systemTime = getSystemTime();
        pos.y += NE_deltaTime*.13;
        pos.x += NE_deltaTime*.14;
        if (pos.x < -1.f) pos.x = 1.f;
        if (pos.x > 1.f) pos.x = -1.f;
        if (pos.y < -1.f) pos.y = 1.f;
        if (pos.y > 1.f) pos.y = -1.f;
        if (NScreen_IsKeyPressed(NE_KEY_r))
            NEnt_add(bball_intf);
        NScreen_BeginFrame(&NE_mousedX, &NE_mousedY);
        {
            NE_Vec3 vel = {0};
            if (NScreen_IsKeyDown(NE_KEY_w)) vel.z += 1.;
            if (NScreen_IsKeyDown(NE_KEY_a)) vel.x -= 1.;
            if (NScreen_IsKeyDown(NE_KEY_s)) vel.z -= 1.;
            if (NScreen_IsKeyDown(NE_KEY_d)) vel.x += 1.;
            if (NScreen_IsKeyDown(NE_KEY_q)) vel.y += 1.;
            if (NScreen_IsKeyDown(NE_KEY_e)) vel.y -= 1.;
            vel = NE_Vec3_Norm(vel);
            vel = NE_Vec3_Scale(vel, NE_deltaTime);
            vel = NE_Vec3_Scale(vel, .5);
            if (NScreen_IsKeyDown(NE_KEY_altL)) vel = NE_Vec3_Scale(vel, .15);
            if (NScreen_IsKeyDown(NE_KEY_shiftL)) vel = NE_Vec3_Scale(vel, 4.);
            NE_TransformW tw = NE_Transform_Cache((NE_Transform) {{0}, {-c_pitch, c_yaw, 0}, {1,1,1}});
            vel = NE_TransformW_Apply(tw, vel);
            c_pos = NE_Vec3_Add(vel, c_pos);
        }
        if (NScreen_IsKeyPressed(NE_KEY_z)) {
            Player_Data pd;
            NE_TransformW tw = NE_Transform_Cache((NE_Transform) {{0}, {-c_pitch, c_yaw, 0}, {1,1,1}});
            NE_Vec3 fd = NE_TransformW_Apply(tw, NE_Vec3_From3(0,0,1));
            pd.pos = NE_Vec3_Add(c_pos, NE_Vec3_Scale(fd, .4));
            pd.vel = NE_Vec3_Scale(fd, .8);
            NEnt_send(NENT_MSG_USR1, NEnt_add(player_intf), &pd);
        }
        if (NScreen_IsKeyDown(NE_KEY_up))
            c_pitch += NE_deltaTime;
        if (NScreen_IsKeyDown(NE_KEY_down))
            c_pitch -= NE_deltaTime;
        if (NScreen_IsKeyDown(NE_KEY_left))
            c_yaw += NE_deltaTime;
        if (NScreen_IsKeyDown(NE_KEY_right))
            c_yaw -= NE_deltaTime;
        c_pitch -= NE_mousedY;
        c_yaw -= NE_mousedX;
        NScreen_RotateCamera(c_yaw, c_pitch, 0);
        NScreen_TranslateCamera(c_pos);
        {
            NE_TransformW tw = NE_Transform_Cache((NE_Transform) {
                    {0,-2,0},
                    {0,0,PI},
                    {100, .1, 100}
                });
            NScreen_RenderModel(player_model, tw);
        }
        NE_Rotation r = NE_Rotation_From_Rad(NE_systemTime);
        NScreen_DrawTriangle_Ex(
            NE_Vec3_Add(pos, NE_Vec3_RotateXY(NE_Vec3_From2(0, .1f),r)),
            NE_Vec3_Add(pos, NE_Vec3_RotateXZ(NE_Vec3_From2(-.1f, -.1f),r)),
            NE_Vec3_Add(pos, NE_Vec3_RotateXZ(NE_Vec3_From2(.1f, -.1f),r)),
            NE_GREEN,
            NE_RED,
            NE_BLUE
            );
        pos.z = sinf(NE_systemTime)*.5f+1.f;
        NEnt_update();
        NScreen_EndFrame();
    }
}

NE_Vec2 NE_Vec2_Rotate(NE_Vec2 v, NE_Rotation r) {return NE_Vec2_From2(v.x*r.cos-v.y*r.sin,v.x*r.sin+v.y*r.cos);}
NE_Vec3 NE_Vec3_RotateXY(NE_Vec3 v, NE_Rotation r) {
    f64 dx = v.x*r.cos-v.y*r.sin, dy = v.x*r.sin+v.y*r.cos;
    v.x = dx;
    v.y = dy;
    return v;
}
NE_Vec3 NE_Vec3_RotateYZ(NE_Vec3 v, NE_Rotation r) {
    f64 dy = v.y*r.cos-v.z*r.sin, dz = v.y*r.sin+v.z*r.cos;
    v.y = dy;
    v.z = dz;
    return v;
}
NE_Vec3 NE_Vec3_RotateXZ(NE_Vec3 v, NE_Rotation r) {
    f64 dx = v.x*r.cos-v.z*r.sin, dz = v.x*r.sin+v.z*r.cos;
    v.x = dx;
    v.z = dz;
    return v;
}

NE_Vec2 NE_Vec2_Add(NE_Vec2 a, NE_Vec2 b) {return NE_Vec2_From2(a.x+b.x,a.y+b.y);}
NE_Vec2 NE_Vec2_Sub(NE_Vec2 a, NE_Vec2 b) {return NE_Vec2_From2(a.x-b.x,a.y-b.y);}
NE_Vec2 NE_Vec2_Mul(NE_Vec2 a, NE_Vec2 b) {return NE_Vec2_From2(a.x*b.x,a.y*b.y);}
NE_Vec2 NE_Vec2_Div(NE_Vec2 a, NE_Vec2 b) {return NE_Vec2_From2(a.x/b.x,a.y/b.y);}
NE_Vec2 NE_Vec2_Scale(NE_Vec2 v, f64 s) {return NE_Vec2_From2(v.x*s,v.y*s);}

NE_Vec3 NE_Vec3_Add(NE_Vec3 a, NE_Vec3 b) {return NE_Vec3_From3(a.x+b.x,a.y+b.y,a.z+b.z);}
NE_Vec3 NE_Vec3_Sub(NE_Vec3 a, NE_Vec3 b) {return NE_Vec3_From3(a.x-b.x,a.y-b.y,a.z-b.z);}
NE_Vec3 NE_Vec3_Mul(NE_Vec3 a, NE_Vec3 b) {return NE_Vec3_From3(a.x*b.x,a.y*b.y,a.z*b.z);}
NE_Vec3 NE_Vec3_Div(NE_Vec3 a, NE_Vec3 b) {return NE_Vec3_From3(a.x/b.x,a.y/b.y,a.z/b.z);}
NE_Vec3 NE_Vec3_Scale(NE_Vec3 v, f64 s) {return NE_Vec3_From3(v.x*s,v.y*s,v.z*s);}

f64     NE_Vec3_MagSq(NE_Vec3 v) {return v.x*v.x+v.y*v.y+v.z*v.z;}
f64     NE_Vec3_Mag(NE_Vec3 v) {return sqrt(v.x*v.x+v.y*v.y+v.z*v.z);}
NE_Vec3 NE_Vec3_Norm(NE_Vec3 v) {
    if (v.x == 0 && v.y == 0 && v.z == 0) return v;
    f64 m = NE_Vec3_Mag(v);
    return NE_Vec3_From3(v.x/m,v.y/m,v.z/m);
}

NE_Vec4 NE_Vec4_Add(NE_Vec4 a, NE_Vec4 b) {return NE_Vec4_From4(a.x+b.x,a.y+b.y,a.z+b.z,a.w+b.w);}
NE_Vec4 NE_Vec4_Sub(NE_Vec4 a, NE_Vec4 b) {return NE_Vec4_From4(a.x-b.x,a.y-b.y,a.z-b.z,a.w-b.w);}
NE_Vec4 NE_Vec4_Mul(NE_Vec4 a, NE_Vec4 b) {return NE_Vec4_From4(a.x*b.x,a.y*b.y,a.z*b.z,a.w*b.w);}
NE_Vec4 NE_Vec4_Div(NE_Vec4 a, NE_Vec4 b) {return NE_Vec4_From4(a.x/b.x,a.y/b.y,a.z/b.z,a.w/b.w);}
NE_Vec4 NE_Vec4_Scale(NE_Vec4 v, f64 s) {return NE_Vec4_From4(v.x*s,v.y*s,v.z*s,v.w*s);}

NE_TransformW NE_Transform_Cache(NE_Transform t) {
    return (NE_TransformW) {
        t.position,
        t.scale,
        NE_Rotation_From_Rad(t.rotation.z),
        NE_Rotation_From_Rad(t.rotation.y),
        NE_Rotation_From_Rad(t.rotation.x),
    };
}

NE_Vec3 NE_TransformW_Apply(NE_TransformW t, NE_Vec3 v) {
    // RST
    v = NE_Vec3_RotateYZ(v, t.cryz);
    v = NE_Vec3_RotateXZ(v, t.crxz);
    v = NE_Vec3_RotateXY(v, t.crxy);

    v = NE_Vec3_Mul(v, t.scale);
    
    v = NE_Vec3_Add(v, t.position);

    return v; 
}
