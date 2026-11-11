// Independent check: colouring string c[0..n-1] over digits; k-term monochromatic AP exists?
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc,char**argv){ if(argc<3){fprintf(stderr,"usage: apcheck file k\n");return 2;}
 FILE*f=fopen(argv[1],"r"); if(!f){perror("open");return 2;}
 static char buf[2000000]; size_t n=fread(buf,1,sizeof buf,f); fclose(f);
 while(n&&(buf[n-1]=='\n'||buf[n-1]=='\r'||buf[n-1]==' '))n--;
 int k=atoi(argv[2]); int colours=0; for(size_t i=0;i<n;i++){ if(buf[i]<'0'||buf[i]>'9'){fprintf(stderr,"bad char at %zu\n",i);return 2;} if(buf[i]-'0'+1>colours)colours=buf[i]-'0'+1; }
 long bad=0;
 for(size_t a=0;a<n;a++) for(size_t d=1;a+(size_t)(k-1)*d<n;d++){ char c=buf[a]; int mono=1; for(int i=1;i<k;i++) if(buf[a+i*d]!=c){mono=0;break;} if(mono){bad++; if(bad<4)printf("MONO AP start=%zu step=%zu colour=%c\n",a+1,d,c);} }
 printf("n=%zu colours=%d k=%d monochromatic_APs=%ld -> %s\n",n,colours,k,bad,bad?"FAIL":"OK (W(colours,k) > n)");
 return bad?1:0; }
