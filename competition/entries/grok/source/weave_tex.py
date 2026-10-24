# v5: procedural tileable knit-jersey fabric maps (normal, roughness, albedo), replacing the Poly Haven Bi-Stretch
# maps whose horizontal ribs read as ripple bands. Output: 1024 px PNGs.
import numpy as np, sys
from PIL import Image
N=1024; out=sys.argv[1]
y,x=np.mgrid[0:N,0:N]/N
C,R=96,128                                   # stitch columns / rows per tile
u=(x*C)%1.0; v=(y*R)%1.0; col=np.floor(x*C)
# each knit stitch = two slanted legs forming a V
leg=np.where(u<0.5, np.abs((u-0.25)-(v-0.5)*0.35), np.abs((u-0.75)+(v-0.5)*0.35))
h=np.clip(1-leg/0.2,0,1)**1.5
h*= 0.75+0.25*np.sin(np.pi*v)                   # loops round off top/bottom
rng=np.random.default_rng(7)
def tnoise(s,amp):                               # tileable low-amplitude yarn variation
    f=np.fft.fft2(rng.standard_normal((N,N))); k=np.fft.fftfreq(N)*N
    K=np.sqrt(k[:,None]**2+k[None,:]**2); f*=np.exp(-(K/s)**2); n=np.real(np.fft.ifft2(f)); return amp*(n-n.mean())/n.std()
h=h+tnoise(200,0.08)
gy,gx=np.gradient(h); s=6.0
n=np.dstack([-gx*s,-gy*s,np.ones_like(h)]); n/=np.linalg.norm(n,axis=2,keepdims=True)
Image.fromarray(((n*0.5+0.5)*255).astype(np.uint8)).save(out+'/knit_nor.png')
r=np.clip(0.82-0.12*h+tnoise(60,0.02),0,1)      # glTF: roughness in G, metal B=0
mr=np.dstack([np.zeros_like(r),r,np.zeros_like(r)])
Image.fromarray((mr*255).astype(np.uint8)).save(out+'/knit_rough.png')
a=np.clip(0.75+0.25*h+tnoise(30,0.03),0,1)      # neutral grey albedo, tinted by baseColorFactor per garment
Image.fromarray((np.dstack([a,a,a])*255).astype(np.uint8)).save(out+'/knit_diff.png')
print('ok')
