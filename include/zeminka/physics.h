#pragma once
#include <zeminka/main.h>

#ifndef DOT3
#define DOT3(x1,y1,z1,x2,y2,z2) (((x1)*(x2))+((y1)*(y2))+((z1)*(z2)))
#endif

void ZEPhysics_cmsolver(f64 m1, ZEVec3 *v1, f64 m2, ZEVec3 *v2);
