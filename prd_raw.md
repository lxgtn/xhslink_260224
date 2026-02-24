准备工作：使用者在确定的Google Sheets表格（https://docs.google.com/spreadsheets/d/1uCEXTte4iZ2DlzpM04AHx9ch2dzPrL4tjfQYa4pInu4/edit?usp=sharing）内填写一个或多个小红书链接（例如：https://www.xiaohongshu.com/explore/699d1873000000001d010f64?xsec_token=ABLZz8df1s0KH3SqjLLQFyTCPMhunarf8J7njGoVhHZW4=&xsec_source=pc_collect），
1. 使用者在一个网页上点击一个按钮，开始运行工作流；
2. 工作流将检测表格内所有auto字段、error字段均为空值的行，将这些行的小红书链接依次投入工作流进行处理；
3. 工作流需要自动抓取每条小红书链接对应笔记的标题(title)、作者(author)、发布时间(date)、收藏量(stars)、笔记文字内容(text_original)、图片地址列表(pic_url_list)、视频地址列表(video_url_list)；
4. 基于第3步抓取到的pic_url_list，工作流需要用深度思考大模型对所有图片进行解析，针对纯视觉图片用简短文字记录下图片中的内容，针对有文字的图片解析出其中的文字，将每张图片解析出的文字内容按照图片顺序依次排列并用数字序号进行标记，形成图片解析内容(pic_processed)；
5. 基于第3步抓取到的video_url_list，工作流需要用深度思考大模型对视频进行解析，分析视频的声音和画面并归纳为结构性的文字内容，形成视频解析内容(video_processed)；
6. 基于每条小红书链接对应笔记的text_original、pic_processed、video_processed数据，工作流需要用深度思考大模型进行处理，形成一篇汇总的笔记内容总结(summary)；
7. 将抓取的、解析的、总结的内容对应整理回原本的Google Sheets表格（https://docs.google.com/spreadsheets/d/1uCEXTte4iZ2DlzpM04AHx9ch2dzPrL4tjfQYa4pInu4/edit?usp=sharing），表格每一行为一条笔记内容，每一列包括初始值（link）、抓取值（title; author; date; stars; text_original; pic_url_list; video_url_list）、以及解析值（pic_processed; video_processed; summary），确认为空值的字段需要占位为0；
8. 工作流需要在最后检查初始任务列表内的所有需要处理的小红书链接是否都已处理完成（即第7步中列举的所有字段均已填写完成），确认处理完成的项目将auto字段改为1，若检测到未完成，则在error字段标注失败原因。