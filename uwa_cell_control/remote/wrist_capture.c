/* Native MJPEG burst for the explicitly requested UWA camera service. MIT. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <poll.h>
#include <linux/videodev2.h>
struct mapped {void *ptr; size_t len;};
static int xi(int fd,unsigned long req,void *arg){int r;do{r=ioctl(fd,req,arg);}while(r<0&&errno==EINTR);return r;}
static void controls(int fd,int frame){
 const unsigned ids[]={V4L2_CID_FOCUS_ABSOLUTE,V4L2_CID_FOCUS_AUTO,V4L2_CID_EXPOSURE_ABSOLUTE,V4L2_CID_EXPOSURE_AUTO,V4L2_CID_GAIN,V4L2_CID_AUTO_WHITE_BALANCE,V4L2_CID_WHITE_BALANCE_TEMPERATURE};
 const char *names[]={"focus_absolute","focus_auto","exposure_absolute","exposure_auto","gain","white_balance_auto","white_balance_temperature"};
 printf("CONTROLS {\"frame\":%d",frame);
 for(unsigned i=0;i<sizeof(ids)/sizeof(ids[0]);i++){
  struct v4l2_control c;memset(&c,0,sizeof c);c.id=ids[i];
  if(xi(fd,VIDIOC_G_CTRL,&c)==0)printf(",\"%s\":%d",names[i],c.value);
 }
 printf("}\n");fflush(stdout);
}
int main(int argc,char **argv){
 if(argc!=3){fprintf(stderr,"Usage: capture_v4l2 DEVICE OUTPUT_DIRECTORY\n");return 2;}
 int fd=open(argv[1],O_RDWR|O_NONBLOCK),rc=1,changed=0,stream=0,haveparm=0,allocated=0;
 struct mapped maps[4];memset(maps,0,sizeof maps);
 struct v4l2_format old,fmt;struct v4l2_streamparm parm;
 memset(&old,0,sizeof old);old.type=V4L2_BUF_TYPE_VIDEO_CAPTURE;
 memset(&parm,0,sizeof parm);parm.type=V4L2_BUF_TYPE_VIDEO_CAPTURE;
 if(fd<0){perror("open");return 1;}
 controls(fd,-2);
 if(xi(fd,VIDIOC_G_FMT,&old)<0){perror("G_FMT");goto done;}
 haveparm=xi(fd,VIDIOC_G_PARM,&parm)==0;
 fmt=old;fmt.fmt.pix.width=2592;fmt.fmt.pix.height=1944;fmt.fmt.pix.pixelformat=V4L2_PIX_FMT_MJPEG;fmt.fmt.pix.field=V4L2_FIELD_ANY;
 if(xi(fd,VIDIOC_S_FMT,&fmt)<0){perror("S_FMT");goto done;}changed=1;
 printf("NEGOTIATED width=%u height=%u sizeimage=%u\n",fmt.fmt.pix.width,fmt.fmt.pix.height,fmt.fmt.pix.sizeimage);fflush(stdout);
 if(fmt.fmt.pix.width!=2592||fmt.fmt.pix.height!=1944||fmt.fmt.pix.pixelformat!=V4L2_PIX_FMT_MJPEG){fprintf(stderr,"Requested native format not accepted\n");goto done;}
 if(haveparm){struct v4l2_streamparm wanted=parm;wanted.parm.capture.timeperframe.numerator=1;wanted.parm.capture.timeperframe.denominator=15;if(xi(fd,VIDIOC_S_PARM,&wanted)<0){perror("S_PARM");goto done;}}
 struct v4l2_requestbuffers req;memset(&req,0,sizeof req);req.type=V4L2_BUF_TYPE_VIDEO_CAPTURE;req.memory=V4L2_MEMORY_MMAP;req.count=4;
 if(xi(fd,VIDIOC_REQBUFS,&req)<0){perror("REQBUFS");goto done;}allocated=1;
 if(req.count<2||req.count>4){fprintf(stderr,"Unexpected buffer count\n");goto done;}
 for(unsigned i=0;i<req.count;i++){
  struct v4l2_buffer b;memset(&b,0,sizeof b);b.type=req.type;b.memory=req.memory;b.index=i;
  if(xi(fd,VIDIOC_QUERYBUF,&b)<0){perror("QUERYBUF");goto done;}
  maps[i].len=b.length;maps[i].ptr=mmap(NULL,b.length,PROT_READ|PROT_WRITE,MAP_SHARED,fd,b.m.offset);
  if(maps[i].ptr==MAP_FAILED){maps[i].ptr=NULL;perror("mmap");goto done;}
  if(xi(fd,VIDIOC_QBUF,&b)<0){perror("QBUF");goto done;}
 }
 enum v4l2_buf_type type=V4L2_BUF_TYPE_VIDEO_CAPTURE;
 if(xi(fd,VIDIOC_STREAMON,&type)<0){perror("STREAMON");goto done;}stream=1;
 for(int frame=0;frame<6;frame++){
  struct pollfd p={fd,POLLIN,0};if(poll(&p,1,2000)<=0){perror("poll timeout");goto done;}
  struct v4l2_buffer b;memset(&b,0,sizeof b);b.type=type;b.memory=V4L2_MEMORY_MMAP;
  if(xi(fd,VIDIOC_DQBUF,&b)<0){perror("DQBUF");goto done;}
  if(b.index>=4||!maps[b.index].ptr||b.bytesused>maps[b.index].len){fprintf(stderr,"Invalid captured buffer\n");goto done;}
  if(b.flags & V4L2_BUF_FLAG_ERROR){fprintf(stderr,"Driver marked frame invalid\n");goto done;}
  printf("FRAME %d bytes=%u sequence=%u flags=%u timestamp=%ld.%06ld\n",frame,b.bytesused,b.sequence,b.flags,(long)b.timestamp.tv_sec,(long)b.timestamp.tv_usec);fflush(stdout);
  if(frame>=3){
   if(frame==3||frame==5)controls(fd,frame);
   char path[4096];if(snprintf(path,sizeof path,"%s/frame_%03d.jpg",argv[2],frame-3)>=(int)sizeof path){fprintf(stderr,"Output path too long\n");goto done;}
   FILE *f=fopen(path,"wb");if(!f){perror("fopen");goto done;}
   size_t n=fwrite(maps[b.index].ptr,1,b.bytesused,f);int closed=fclose(f);
   if(n!=b.bytesused||closed){fprintf(stderr,"File write failed\n");goto done;}
   if(frame==5)rc=0;
  }
  if(xi(fd,VIDIOC_QBUF,&b)<0){perror("requeue");rc=1;goto done;}
 }
done:
 if(stream){enum v4l2_buf_type type=V4L2_BUF_TYPE_VIDEO_CAPTURE;if(xi(fd,VIDIOC_STREAMOFF,&type)<0){perror("STREAMOFF");rc=1;}}
 for(int i=0;i<4;i++)if(maps[i].ptr)munmap(maps[i].ptr,maps[i].len);
 if(allocated){struct v4l2_requestbuffers req;memset(&req,0,sizeof req);req.type=V4L2_BUF_TYPE_VIDEO_CAPTURE;req.memory=V4L2_MEMORY_MMAP;if(xi(fd,VIDIOC_REQBUFS,&req)<0){perror("free buffers");rc=1;}}
 if(changed){if(xi(fd,VIDIOC_S_FMT,&old)<0){perror("restore format");rc=1;}else printf("RESTORED_FORMAT %ux%u\n",old.fmt.pix.width,old.fmt.pix.height);if(haveparm&&xi(fd,VIDIOC_S_PARM,&parm)<0){perror("restore rate");rc=1;}}
 close(fd);return rc;
}
