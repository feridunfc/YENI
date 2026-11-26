"""Independent C35 fixed-compression section check for the physical two-storey example."""
from math import acos, cos, hypot, pi, sin, sqrt


def concrete_strip(width, depth, nx, ny, cut):
    """Integrate rectangular area and first moments in vertical strips.

    Split at the two face intersections. The three integrands are then at
    most quadratic and Simpson quadrature is exact on each subinterval.
    """
    if abs(nx) > abs(ny):
        area, qy, qx = concrete_strip(depth,width,ny,nx,cut)
        return area, qx, qy
    a,b=width/2,depth/2
    knots=[-a,a]
    if abs(nx)>1e-15:
        knots.extend(x for y in (-b,b) if -a < (x:=(cut-ny*y)/nx) < a)
    knots.sort()
    totals=[0.,0.,0.]
    for lo,hi in zip(knots,knots[1:]):
        for x,weight in ((lo,1),((lo+hi)/2,4),(hi,1)):
            y=max(-b,min(b,(cut-nx*x)/ny))
            lower,upper=(y,b) if ny>0 else (-b,y)
            scale=weight*(hi-lo)/6
            totals[0]+=scale*(upper-lower)
            totals[1]+=scale*x*(upper-lower)
            totals[2]+=scale*(upper**2-lower**2)/2
    return totals


def independent_capacity(native, chosen, cut):
    width, depth = native["t2_mm"],native["t3_mm"]
    if native["fck_mpa"]!=35:
        raise ValueError("G2 section oracle requires the documented C35 block")
    d=chosen["diameter_mm"]
    r=d/2
    area=pi*r*r
    offset=native["cover_to_tie_mm"]+chosen["selected_transverse"]["tie_diameter_mm"]+r
    def stations(n,extent):
        return [(extent/2-offset)*(2*i/(n-1)-1) for i in range(n)]
    xs=stations(chosen["num_bars_2_dir"],width)
    ys=stations(chosen["num_bars_3_dir"],depth)
    bars=[(x,y) for x in xs for y in (ys[0],ys[-1])]+[(x,y) for x in (xs[0],xs[-1]) for y in ys[1:-1]]
    if len(set(bars))!=chosen["bar_count"] or abs(len(bars)*area-chosen["area_mm2"])>1e-6:
        raise ValueError("Independent perimeter steel census")
    m2,m3=(cut["magnified_"+k+"_design_knm"] for k in ("m2","m3"))
    demand=hypot(m2,m3)
    u,v=m2/demand,m3/demand
    concrete=.85*native["fcd_mpa"]
    steel=native["fyd_mpa"]
    target=cut["nd_kn"]*1000
    def at_angle(theta):
        nx,ny=cos(theta),sin(theta)
        extreme=(width*abs(nx)+depth*abs(ny))/2
        depths=[nx*x+ny*y for x,y in bars]
        lo,hi=0.,10*hypot(width,depth)
        for i in range(54):
            c=(lo+hi)/2
            line=extreme-.79*c
            ac,qx,qy=concrete_strip(width,depth,nx,ny,line)
            n,mx,my=concrete*ac,concrete*qy,concrete*qx
            for (x,y),q in zip(bars,depths):
                force=area*max(-steel,min(steel,.003*native["es_mpa"]*(1-(extreme-q)/c)))
                z=line-q
                if z <= -r:
                    force-=concrete*area
                elif z < r:
                    half=sqrt(max(0.,r*r-z*z))
                    force-=concrete*(r*r*acos(z/r)-z*half)
                    first=2*half**3/3
                    mx-=concrete*ny*first
                    my-=concrete*nx*first
                n+=force
                mx+=force*y
                my+=force*x
            if n<target:
                lo=c
            else:
                hi=c
        return mx*v-my*u,(mx*u+my*v)/1e6,abs(n-target)
    # Include a fractional angular offset to bracket roots on both principal axes.
    lo=.007
    left=at_angle(lo)
    roots=[]
    for i in range(1,17):
        hi=.007+2*pi*i/16
        right=at_angle(hi)
        if right[0]*left[0] <= 0:
            a,b=lo,hi
            for _ in range(46):
                mid=(a+b)/2
                row=at_angle(mid)
                if row[0]*left[0] > 0:
                    a=mid
                else:
                    b=mid
            roots.append(row)
        lo,left=hi,right
    positive=[s for s in roots if s[1]>0]
    if len(roots)!=2 or len(positive)!=1:
        raise ArithmeticError("Independent signed radial capacity is ambiguous")
    cross,capacity,residual=positive[0]
    difference=abs(capacity-cut["radial_capacity_knm"])
    if residual>.001 or abs(cross)>.001 or difference>.01:
        raise ArithmeticError(f"Independent PMM residuals {residual}, {cross}, {difference}")
    return {"capacity_knm":capacity,"production_knm":cut["radial_capacity_knm"],"difference_knm":difference,
            "axial_residual_n":residual,"perpendicular_residual_nmm":abs(cross),"utilization":demand/capacity}
