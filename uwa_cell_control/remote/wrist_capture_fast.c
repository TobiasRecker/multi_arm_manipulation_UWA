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

/* Saved on this controller with this exact helper/ABI, never supplied by a client. */
struct original_mode {struct v4l2_format format;struct v4l2_streamparm rate;int have_rate;};
static int save_mode(const char *directory,struct v4l2_format *fmt,struct v4l2_streamparm *rate,int have){
 char path[4096];if(snprintf(path,sizeof path,"%s/original-v4l2-mode.bin",directory)>=(int)sizeof path)return -1;
 struct original_mode mode;memset(&mode,0,sizeof mode);mode.format=*fmt;mode.rate=*rate;mode.have_rate=have;
 FILE *f=fopen(path,"wb");if(!f)return -1;
 int ok=fwrite(&mode,sizeof mode,1,f)==1;int closed=fclose(f);return ok&&!closed?0:-1;
}
static int mode_command(const char *command,const char *device,const char *directory){
 char path[4096];if(snprintf(path,sizeof path,"%s/original-v4l2-mode.bin",directory)>=(int)sizeof path)return 2;
 struct original_mode old;FILE *f=fopen(path,"rb");if(!f){perror("original mode");return 2;}
 int read_ok=fread(&old,sizeof old,1,f)==1;fclose(f);if(!read_ok)return 2;
 int fd=open(device,O_RDWR|O_NONBLOCK);if(fd<0){perror("mode open");return 2;}
 struct v4l2_format actual;memset(&actual,0,sizeof actual);actual.type=V4L2_BUF_TYPE_VIDEO_CAPTURE;
 struct v4l2_streamparm rate;memset(&rate,0,sizeof rate);rate.type=actual.type;
 int rc=1;
 if(!strcmp(command,"--restore-mode")){
  if(xi(fd,VIDIOC_S_FMT,&old.format)<0){perror("fallback S_FMT");goto end;}
  if(old.have_rate&&xi(fd,VIDIOC_S_PARM,&old.rate)<0){perror("fallback S_PARM");goto end;}
 }
 if(xi(fd,VIDIOC_G_FMT,&actual)<0){perror("verify G_FMT");goto end;}
 if(old.have_rate&&xi(fd,VIDIOC_G_PARM,&rate)<0){perror("verify G_PARM");goto end;}
 if(actual.fmt.pix.width!=old.format.fmt.pix.width||actual.fmt.pix.height!=old.format.fmt.pix.height||actual.fmt.pix.pixelformat!=old.format.fmt.pix.pixelformat){fprintf(stderr,"Restored format differs from original\n");goto end;}
 if(old.have_rate && ((unsigned long long)rate.parm.capture.timeperframe.numerator*old.rate.parm.capture.timeperframe.denominator!=(unsigned long long)old.rate.parm.capture.timeperframe.numerator*rate.parm.capture.timeperframe.denominator)){fprintf(stderr,"Restored frame interval differs from original\n");goto end;}
 printf("{\"verified\":true,\"width\":%u,\"height\":%u,\"fourcc\":%u,\"frame_interval\":[%u,%u]}\n",actual.fmt.pix.width,actual.fmt.pix.height,actual.fmt.pix.pixelformat,rate.parm.capture.timeperframe.numerator,rate.parm.capture.timeperframe.denominator);rc=0;
end:close(fd);return rc;
}

int main(int argc,char **argv){
 if(argc==4 && (!strcmp(argv[1],"--verify-mode")||!strcmp(argv[1],"--restore-mode")))return mode_command(argv[1],argv[2],argv[3]);
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
 if(save_mode(argv[2],&old,&parm,haveparm)<0){perror("save original mode");goto done;}
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
 int retained=0;
 for(int frame=0;frame<32 && retained<3;frame++){
  struct pollfd p={fd,POLLIN,0};if(poll(&p,1,2000)<=0){perror("poll timeout");goto done;}
  struct v4l2_buffer b;memset(&b,0,sizeof b);b.type=type;b.memory=V4L2_MEMORY_MMAP;
  if(xi(fd,VIDIOC_DQBUF,&b)<0){perror("DQBUF");goto done;}
  if(b.index>=4||!maps[b.index].ptr||b.bytesused>maps[b.index].len){fprintf(stderr,"Invalid captured buffer\n");goto done;}
  int valid=!(b.flags & V4L2_BUF_FLAG_ERROR) && b.bytesused>=4;
  unsigned char *bytes=maps[b.index].ptr;
  if(valid && (bytes[0]!=0xff || bytes[1]!=0xd8))valid=0;
  int eoi=0;
  if(valid)for(unsigned j=2;j+1<b.bytesused;j++)if(bytes[j]==0xff && bytes[j+1]==0xd9){eoi=1;break;}
  if(!eoi)valid=0;
  printf("FRAME %d bytes=%u sequence=%u flags=%u timestamp=%ld.%06ld\n",frame,b.bytesused,b.sequence,b.flags,(long)b.timestamp.tv_sec,(long)b.timestamp.tv_usec);fflush(stdout);
  if(frame>=3 && valid){
   char path[4096];if(snprintf(path,sizeof path,"%s/frame_%03d.jpg",argv[2],retained)>=(int)sizeof path){fprintf(stderr,"Output path too long\n");goto done;}
   FILE *f=fopen(path,"wb");if(!f){perror("fopen");goto done;}
   size_t n=fwrite(maps[b.index].ptr,1,b.bytesused,f);int closed=fclose(f);
   if(n!=b.bytesused||closed){fprintf(stderr,"File write failed\n");goto done;}
   /* Read UVC controls only after this dequeued image has been copied. Logical
      frame3/frame5 mean first/last retained image; raw sequence stays above. */
   if(retained==0||retained==2)controls(fd,3+retained);
   retained++;
   if(retained==3)rc=0;
  }
  if(!valid)printf("DISCARDED invalid JPEG frame=%d\n",frame);
  if(xi(fd,VIDIOC_QBUF,&b)<0){perror("requeue");rc=1;goto done;}
 }
 if(retained<3)fprintf(stderr,"Not enough valid native JPEG frames\n");
done:
 if(stream){enum v4l2_buf_type type=V4L2_BUF_TYPE_VIDEO_CAPTURE;if(xi(fd,VIDIOC_STREAMOFF,&type)<0){perror("STREAMOFF");rc=1;}}
 for(int i=0;i<4;i++)if(maps[i].ptr)munmap(maps[i].ptr,maps[i].len);
 if(allocated){struct v4l2_requestbuffers req;memset(&req,0,sizeof req);req.type=V4L2_BUF_TYPE_VIDEO_CAPTURE;req.memory=V4L2_MEMORY_MMAP;if(xi(fd,VIDIOC_REQBUFS,&req)<0){perror("free buffers");rc=1;}}
 if(changed)printf("DEFERRED_FORMAT_RESTORE %ux%u via visionserver; verification required\n",old.fmt.pix.width,old.fmt.pix.height);
 close(fd);return rc;
}
