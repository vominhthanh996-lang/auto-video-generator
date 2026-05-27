import json
from pathlib import Path

project = Path(r'E:\ThanhMV\video-projects\novel-chapter-12')
project.mkdir(parents=True, exist_ok=True)
(project / 'assets').mkdir(exist_ok=True)
(project / 'output').mkdir(exist_ok=True)

base_style = 'cinematic realistic vertical 9:16 novel illustration, apocalyptic survival thriller mood, young Asian man Hàn Thiên Dực, realistic lighting, dramatic shadows, premium film still, 35mm cinema lens, atmospheric perspective, natural colors, no text, no watermark'

scenes = [
    {
        'id': 'full-01-water-delivery',
        'text': 'Một đơn hàng kỳ lạ được giao tới.',
        'subtitle': 'Một trăm thùng nước loại cực đại được đưa đến trước cửa nhà.',
        'narration': '''Hàn Thiên Dực sau khi cân nhắc kỹ lưỡng, lập tức liên hệ dịch vụ chuyển phát nhanh, đặt riêng cho mình một đơn hàng cực kỳ đặc biệt. Chỉ trong vòng một ngày, một chiếc xe tải thùng lớn đã lăn bánh đến trước cửa nhà hắn, mang theo đủ một trăm chiếc thùng nước loại cực đại. Mỗi chiếc đều có dung tích khổng lồ, phải cần hai người trưởng thành mới có thể khiêng nổi. Tiểu ca giao hàng toát mồ hôi nhễ nhại, vừa đặt từng thùng xuống vừa không nhịn được tò mò: Anh Hàn, nhà anh mở xưởng nước giải khát sao mà cần nhiều thùng nước thế này? Hàn Thiên Dực chỉ cười nhạt, không giải thích thêm. Trong mắt người ngoài, hành động của hắn quả thực hết sức kỳ quái, chẳng khác nào một trò cười. Nhưng chỉ có hắn biết rõ, những thứ này chính là mạng sống của hắn, là lá chắn duy nhất để chống chọi với tương lai tận thế đang đến gần.''',
        'prompt': 'large delivery truck parked before a modern house, workers unloading many huge blue water barrels, sweaty courier asking a question, young Asian man smiling faintly and hiding the truth, tense survival preparation atmosphere, ' + base_style,
    },
    {
        'id': 'full-02-filling-water',
        'text': 'Cả căn nhà vang lên tiếng nước chảy.',
        'subtitle': 'Hắn mở hết vòi nước, lấp đầy từng thùng lớn.',
        'narration': '''Ngay sau khi xe tải rời đi, hắn không hề chần chừ mà bắt tay ngay vào việc. Từng vòi nước trong căn nhà đều được vặn mở tối đa. Nước từ hệ thống cấp chảy ào ào như thác, rót vào từng chiếc thùng lớn xếp khắp phòng khách, phòng bếp, thậm chí cả hành lang và sân sau. Tiếng nước dội ào ạt vang vọng khắp căn nhà, tạo thành một khung cảnh vừa khẩn trương vừa có phần điên cuồng. Theo tính toán của hắn, với tốc độ này, nhiều nhất chỉ cần khoảng một tuần, toàn bộ một trăm thùng nước đều có thể được lấp đầy. Đủ lượng nước này, nếu biết cách tiết kiệm, hắn có thể sống sót qua nhiều tháng dài lạnh lẽo.''',
        'prompt': 'inside a house packed with huge water barrels, every faucet open, water pouring into containers, wet reflective floor, urgent and slightly manic survival preparation, young Asian man moving quickly between rooms, ' + base_style,
    },
    {
        'id': 'full-03-money-loses-meaning',
        'text': 'Tiền bạc sắp trở thành vô nghĩa.',
        'subtitle': 'Hắn dùng từng đồng cuối cùng để chuẩn bị cho tận thế.',
        'narration': '''Thời gian trôi đi từng ngày. Trong suốt những ngày ấy, Hàn Thiên Dực hầu như không có một phút nào rảnh rỗi. Hắn đem từng đồng tiền mà mình có ra dùng đến mức tận cùng, không hề tiếc rẻ hay do dự. Mỗi bữa ăn đều được chọn ở những nhà hàng tốt nhất, những nơi trước đây hắn không bao giờ dám bước vào vì giá cả quá đắt đỏ. Nhưng giờ đây, tiền bạc đối với hắn đã mất đi ý nghĩa lâu dài. Hắn biết rõ, chỉ vài chục ngày nữa thôi, toàn bộ thế giới tài chính, thương mại, những con số trong ngân hàng, tất cả đều sẽ hóa thành hư vô.''',
        'prompt': 'young Asian man eating alone in an expensive restaurant while looking cold and distant, luxury food on table, city lights outside window, sense that money is becoming meaningless before apocalypse, ' + base_style,
    },
    {
        'id': 'full-04-stockpiling-supplies',
        'text': 'Vật tư chất chồng trong không gian dị giới.',
        'subtitle': 'Thực phẩm, rượu vang, đồ khô và hàng cao cấp được tích trữ không ngừng.',
        'narration': '''Hắn mua số lượng lớn các loại thực phẩm chế biến sẵn, đồ ăn khô, thịt muối, các loại gia vị, rượu vang, thậm chí cả những món ăn cao cấp đóng gói sẵn từ những nhà hàng hạng sang. Tất cả được cẩn thận đưa vào không gian dị giới mà hắn sở hữu, nơi chứa trữ không hề có giới hạn. Từng thùng hàng biến mất khỏi hiện thực, nhưng trong lòng Hàn Thiên Dực, cảm giác an toàn vẫn chưa thật sự đủ đầy. Hắn biết rõ, tận thế không chỉ là đói khát, mà còn là hỗn loạn, lạnh giá và sự tàn nhẫn của con người khi bị đẩy đến đường cùng.''',
        'prompt': 'dim apartment filled with stacks of canned food, dried meat, wine bottles, restaurant meal boxes and survival supplies, surreal faint portal-like storage space effect, young Asian man organizing supplies, ' + base_style,
    },
    {
        'id': 'full-05-combat-training',
        'text': 'Hắn bắt đầu luyện chiến đấu.',
        'subtitle': 'Cung nỏ, súng ngắn, súng trường, từng ngày đều không dừng lại.',
        'narration': '''Ngoài việc mua sắm thực phẩm, Hàn Thiên Dực còn dành phần lớn thời gian của mình cho việc rèn luyện kỹ năng chiến đấu. Mỗi ngày, hắn đều đến trường bắn ở Thiên Hải Thị Trường. Tại đây, hắn thuê riêng phòng tập, miệt mài luyện cung nỏ, súng ngắn, súng trường. Từng phát tên, từng viên đạn rít lên trong không gian, phản chiếu ánh mắt quyết liệt của hắn. Hắn biết rằng, chỉ dựa vào sức mạnh cơ bắp đơn thuần thì không thể trở thành cao thủ trong vòng một tháng ngắn ngủi.''',
        'prompt': 'indoor shooting range, determined young Asian man training with pistol rifle and crossbow, targets full of holes, flying shell casings, harsh industrial light, survival training intensity, ' + base_style,
    },
    {
        'id': 'full-06-safe-house-confidence',
        'text': 'Vũ khí và phòng an toàn là chỗ dựa cuối cùng.',
        'subtitle': 'Hắn chỉ cần đủ kỹ năng để không sợ nguy hiểm ập đến.',
        'narration': '''Nhưng nếu có vũ khí trong tay, cộng thêm kỹ năng dù chỉ ở mức trung bình, lại cộng hưởng với siêu cấp phòng an toàn bằng kim loại mà hắn đã chuẩn bị, hắn có thể đảm bảo một điều: bản thân sẽ không phải e ngại bất kỳ mối nguy hiểm nào ập đến. Mỗi lần nâng súng, mỗi lần kéo dây cung, Hàn Thiên Dực đều tưởng tượng đến thế giới băng giá trong trí nhớ. Ở đó, lòng tốt là thứ xa xỉ, vật tư là luật lệ, và kẻ chậm tay sẽ không còn cơ hội sống sót.''',
        'prompt': 'metal reinforced safe room concept, young Asian man holding a crossbow and pistol near a heavy steel door, cold survival bunker lighting, future apocalypse memory atmosphere, ' + base_style,
    },
    {
        'id': 'full-07-people-mock-him',
        'text': 'Mọi người đều cho rằng hắn phát điên.',
        'subtitle': 'Ánh mắt xa lánh xuất hiện từ hàng xóm, đồng nghiệp và cả Lâm Tuyết Dao.',
        'narration': '''Hành động điên cuồng và khác người như vậy tất nhiên không thể thoát khỏi ánh mắt của những người xung quanh. Từ hàng xóm, bạn bè cho đến đồng nghiệp, tất cả đều nhìn hắn bằng ánh mắt khác lạ. Trong mắt họ, Hàn Thiên Dực chẳng khác gì một kẻ có vấn đề về thần kinh. Họ lắc đầu, cười nhạt sau lưng, cho rằng hắn đang phí phạm tiền bạc, đang sống trong ảo tưởng kỳ quái. Ngay cả Lâm Tuyết Dao, người từng thân thiết với hắn, cũng dần dần tạo khoảng cách. Cô không còn chủ động bắt chuyện, không còn thường xuyên đến tìm hắn như trước nữa.''',
        'prompt': 'apartment corridor with neighbors whispering and judging, young Asian man walking past silently with cold expression, a beautiful woman watching from distance with alienation, social isolation before apocalypse, ' + base_style,
    },
    {
        'id': 'full-08-countdown-twenty-days',
        'text': 'Hơn hai mươi ngày trôi qua.',
        'subtitle': 'Vật tư như núi, nhưng hắn vẫn chưa thấy đủ an toàn.',
        'narration': '''Ánh mắt cô khi nhìn hắn thấp thoáng chút xa lánh, như thể sợ bị cuốn vào sự điên rồ đó. Nhưng Hàn Thiên Dực không hề quan tâm. Hắn lặng lẽ tiếp tục công việc của mình, để mặc cho những lời chế giễu. Ngày lại ngày trôi qua, chẳng mấy chốc đã hơn hai mươi ngày. Khoảng cách đến thời khắc tận thế trong trí nhớ của hắn đã không còn xa. Trong không gian trữ vật của hắn lúc này, vật tư chất chồng như núi: thực phẩm, nước uống, vũ khí, thiết bị sưởi ấm, đủ loại. Nhưng trong thâm tâm, Hàn Thiên Dực vẫn chưa cảm thấy an toàn tuyệt đối.''',
        'prompt': 'young Asian man alone in a dark room looking at a calendar countdown, ghostly vision of massive supplies stacked like mountains in another space, cold blue apocalypse mood, ' + base_style,
    },
    {
        'id': 'full-09-target-walmart',
        'text': 'Mục tiêu lớn nhất xuất hiện.',
        'subtitle': 'Kho hàng siêu cấp của Wal-Mart chứa lượng vật tư khổng lồ.',
        'narration': '''Hắn hiểu rằng, muốn thực sự đảm bảo sống sót lâu dài, hắn cần nhiều hơn thế. Chính vì vậy, hắn quyết định ra tay với mục tiêu lớn nhất: kho hàng siêu cấp của Wal-Mart. Nơi đó chứa lượng vật tư khổng lồ, vượt xa bất kỳ cửa hàng hay chợ nào khác. Nếu có thể chiếm được toàn bộ, hắn sẽ nắm trong tay khối tài nguyên đủ để dùng không chỉ cho một đời, mà có lẽ cho mười đời sau cũng chưa hết. Ý nghĩ ấy vừa điên cuồng vừa lạnh lùng, nhưng đối với Hàn Thiên Dực, đó là lựa chọn hợp lý nhất trong thời điểm cuối cùng.''',
        'prompt': 'massive Walmart-like distribution warehouse at night, huge industrial building under cold lights, young Asian man watching from shadow with determined expression, heist before apocalypse mood, ' + base_style,
    },
    {
        'id': 'full-10-night-shift',
        'text': 'Đêm đó, hắn trở lại kho hàng.',
        'subtitle': 'Ca trực đêm chỉ còn khoảng mười người.',
        'narration': '''Một đêm, hắn lặng lẽ quay lại nhà kho, vẫn như bình thường lên ca trực. Wal-Mart duy trì giám sát hai mươi bốn trên hai mươi bốn, nhưng vào ban đêm, số lượng nhân viên trực giảm xuống chỉ còn khoảng mười người. Với hắn, đó là thời cơ tốt nhất để hành động. Kế hoạch của Hàn Thiên Dực rất đơn giản nhưng lại cực kỳ hiệu quả: hắn lén bỏ thuốc ngủ vào bình trà mà mọi người thường uống trong ca đêm. Chỉ một lát sau, từng nhân viên gục xuống bàn, ngủ say như chết.''',
        'prompt': 'night shift break room inside a huge warehouse, tired employees falling asleep at tables, tea bottle on table, young Asian supervisor standing calmly in shadow, suspense thriller scene, ' + base_style,
    },
    {
        'id': 'full-11-cameras-off',
        'text': 'Camera giám sát tắt phụt.',
        'subtitle': 'Từng màn hình tối đen, kế hoạch chính thức bắt đầu.',
        'narration': '''Khoảng cách đến ngày tận thế chỉ còn chưa đầy một tuần, hắn không còn lo ngại việc bị điều tra. Dù có ai đó nghi ngờ, thì tất cả sẽ chẳng còn ý nghĩa gì khi thế giới sụp đổ. Sau khi chắc chắn thuốc phát huy tác dụng, hắn lập tức đi đến phòng quan sát, tắt toàn bộ hệ thống camera giám sát. Từng màn hình tối đen, không còn ánh sáng nhấp nháy. Hoàn tất bước này, hắn nhanh chóng tiến thẳng vào khu vực kho hàng rộng lớn. Đứng trước tòa nhà kho khổng lồ, Hàn Thiên Dực hít sâu một hơi. Một cảm giác vừa hồi hộp vừa phấn khích dâng tràn.''',
        'prompt': 'security control room with surveillance monitors turning black one by one, young Asian man in warehouse uniform pressing controls, tense cinematic lighting, secret heist atmosphere, ' + base_style,
    },
    {
        'id': 'full-12-drinks-vanish',
        'text': 'Khu đồ uống biến mất trong chớp mắt.',
        'subtitle': 'Nước khoáng, bia rượu và rượu vang bị quét sạch.',
        'narration': '''Hắn bắt đầu sử dụng năng lực đặc thù của mình. Chỉ cần ánh mắt lướt qua kệ hàng, chỉ cần một niệm động tâm, toàn bộ vật tư sẽ lập tức biến mất khỏi hiện trường, chuyển thẳng vào không gian dị giới. Hắn mở màn ở khu đồ uống. Trước mắt hắn là hàng trăm ngàn thùng nước khoáng, nước ngọt, bia, rượu vang, rượu mạnh từ đủ thương hiệu nổi tiếng trên thế giới. Từng thùng, từng chai đều biến mất trong chớp mắt, để lại khoảng trống khổng lồ trên các kệ. Chỉ trong thời gian ngắn, một lượng rượu bia khổng lồ trị giá hàng chục triệu đã biến mất sạch sẽ.''',
        'prompt': 'enormous warehouse beverage aisle, pallets of bottled water soda beer and wine vanishing into a subtle glowing spatial distortion, young Asian man standing with focused eyes, shelves becoming empty, supernatural survival heist, ' + base_style,
    },
    {
        'id': 'full-13-fuel-supplies',
        'text': 'Nhiên liệu là vàng ròng của kỷ băng hà.',
        'subtitle': 'Than, cồn và xăng được gom sạch không chút do dự.',
        'narration': '''Tiếp theo, hắn tiến đến khu nhiên liệu và vật dụng sinh hoạt. Nơi đây chất đống hàng vạn bao than, thùng cồn, thùng xăng, vốn chỉ dùng cho gia đình hoặc dã ngoại. Đối với Hàn Thiên Dực, đây chính là vàng ròng trong kỷ nguyên băng giá sắp tới. Không do dự, hắn gom sạch, rồi còn tỉ mỉ phân khu trong không gian dị giới để tiện cho việc sử dụng sau này. Trong đầu hắn đã hiện lên cảnh tuyết trắng phủ kín thành phố, nhiệt độ rơi xuống mức con người khó lòng chịu nổi. Khi đó, những thứ này sẽ quyết định ai được sống và ai sẽ chết cóng trong tuyệt vọng.''',
        'prompt': 'warehouse aisle filled with coal bags alcohol fuel cans camping supplies, items disappearing into invisible storage space, young Asian man planning calmly, cold future ice age vision overlay, ' + base_style,
    },
    {
        'id': 'full-14-food-aisles',
        'text': 'Khu thực phẩm bị quét sạch.',
        'subtitle': 'Đồ hộp, thịt nguội, gà quay, mì ăn liền không còn sót lại.',
        'narration': '''Bước thứ ba, hắn lao vào khu thực phẩm. Cảnh tượng trước mắt khiến hắn choáng ngợp: từng dãy kệ kéo dài bất tận, chứa đủ loại đồ ăn. Đồ hộp, thịt nguội, gà quay đóng gói, bánh quy, mì ăn liền, đồ ăn vặt cao cấp. Hắn không bỏ sót thứ gì, tất cả đều bị quét sạch. Những dãy kệ vốn nặng trĩu hàng hóa lần lượt trở nên trống rỗng. Âm thanh trong kho vẫn yên tĩnh đến đáng sợ, nhưng bên trong không gian dị giới của hắn, vật tư đang chất lên như núi.''',
        'prompt': 'huge warehouse food section with endless aisles of canned food instant noodles packaged roast chicken snacks, shelves emptying rapidly through supernatural storage power, young Asian man walking alone, ' + base_style,
    },
    {
        'id': 'full-15-sports-cold-gear',
        'text': 'Hắn tìm thấy bảo vật cho thời kỳ băng hà.',
        'subtitle': 'Thiết bị leo núi, trượt tuyết và đồ chống lạnh đều bị gom sạch.',
        'narration': '''Sau thực phẩm, hắn chuyển qua khu thể thao. Ban đầu, hắn chỉ định gom một số máy tập để tăng cường thể lực, nhưng bất ngờ phát hiện nhiều món đồ có thể dùng như vũ khí: gậy bóng chày, kiếm đấu thể thao, cùng đủ loại dụng cụ cứng chắc. Thậm chí, hắn còn tìm thấy thiết bị leo núi, trượt tuyết chuyên dụng đạt chuẩn quốc gia, có khả năng chống chọi nhiệt độ âm cả trăm độ C. Những thứ này trong thời kỳ băng hà sắp tới chính là bảo vật vô giá. Ánh mắt Hàn Thiên Dực sáng rực. Hắn vơ hết, không bỏ sót dù chỉ một đôi găng hay một túi ngủ chuyên dụng.''',
        'prompt': 'warehouse sports section filled with baseball bats fencing swords mountain climbing gear ski suits thermal sleeping bags, young Asian man discovering valuable cold survival equipment, excited intense eyes, ' + base_style,
    },
    {
        'id': 'full-16-empty-warehouse',
        'text': 'Hai giờ sau, kho hàng trống rỗng.',
        'subtitle': 'Cả tòa nhà rộng lớn biến thành khoảng không lạnh lẽo.',
        'narration': '''Cứ thế, trong vòng hai giờ đồng hồ, toàn bộ nhà kho rộng hàng trăm ngàn mét vuông của Wal-Mart đã hoàn toàn trống rỗng, biến thành một khoảng không mênh mông lạnh lẽo. Nhìn cảnh tượng ấy, lòng Hàn Thiên Dực dâng trào sự thỏa mãn chưa từng có. Giờ đây, cho dù tận thế băng giá có đến, hắn cũng tin rằng bản thân sẽ đủ khả năng sống sót an toàn. Hoàn thành xong, hắn quay lại phòng làm việc, giả bộ như mọi thứ bình thường. Thậm chí, để che mắt, hắn còn uống một ngụm trà có pha thuốc ngủ rồi giả vờ gục xuống bàn.''',
        'prompt': 'enormous empty warehouse interior with endless bare shelves, cold industrial lights, young Asian man standing alone satisfied then returning to office desk pretending to sleep, surreal apocalypse heist aftermath, ' + base_style,
    },
    {
        'id': 'full-17-employees-awaken',
        'text': 'Tiếng gọi hốt hoảng vang lên.',
        'subtitle': 'Kho của chúng ta bị người ta dọn sạch rồi!',
        'narration': '''Không biết đã trôi qua bao lâu, hắn bị đánh thức bởi những tiếng gọi hốt hoảng. Chủ quản, chủ quản, mau dậy đi! Có chuyện lớn rồi! Hàn Thiên Dực giả vờ ngái ngủ, từ từ mở mắt, nhìn thấy mấy đồng sự với vẻ mặt hoảng loạn. Chuyện gì thế? Hắn hỏi bằng giọng khàn khàn. Một nhân viên run rẩy chỉ ra phía nhà kho, giọng như sắp khóc: Kho, kho của chúng ta, bị người ta dọn sạch rồi! Cái gì? Hàn Thiên Dực bật dậy, giả bộ kinh ngạc đến cực điểm.''',
        'prompt': 'warehouse office at dawn, panicked employees waking up their supervisor, young Asian man pretending to be shocked after fake sleep, nervous faces, thriller drama lighting, ' + base_style,
    },
    {
        'id': 'full-18-report-superior',
        'text': 'Không ai hiểu chuyện gì đã xảy ra.',
        'subtitle': 'Một kho hàng trị giá khổng lồ biến mất không dấu vết.',
        'narration': '''Hắn cùng mọi người chạy ra nhà kho. Trước mắt bọn họ, cả tòa nhà vốn chất đầy vật tư giờ đây chỉ còn lại không gian rỗng tuếch. Những dãy kệ trống trơn kéo dài vô tận, không còn sót lại bất cứ dấu vết nào. Tất cả nhân viên đều chết lặng. Không thể nào! Trong kho có giá trị ít nhất cả trăm tỷ, làm sao có thể biến mất chỉ trong nháy mắt? Đúng vậy! Cho dù có hàng trăm xe tải cùng đến chở đi thì cũng phải mất mấy ngày mới hết. Đây là quỷ quái gì vậy? Không ai nhắc đến việc họ đã lén ngủ gật trong ca trực. Ai cũng ngầm hiểu, đó là chuyện thường thấy. Hàn Thiên Dực giả bộ lo lắng, hai chân mềm nhũn, giọng run rẩy. Trời ơi, chuyện này rốt cuộc là sao? Cuối cùng hắn mới lên tiếng: Chuyện này vượt ngoài khả năng của chúng ta. Phải báo lên cấp trên ngay thôi. Tất cả đồng ý. Ngay lập tức, Hàn Thiên Dực gọi điện cho quản lý cấp cao của nhà kho. Đầu dây bên kia, người quản lý nghe tin tức mà sững sờ, thậm chí còn tưởng hắn đang đùa.''',
        'prompt': 'group of shocked warehouse employees standing in a vast completely empty warehouse, endless empty shelves, young Asian supervisor pretending panic while secretly calm, phone call to superior, impossible mystery atmosphere, ' + base_style,
    },
]

for i, scene in enumerate(scenes, 1):
    scene['duration'] = 90
    scene['image'] = f'assets/full-scene-{i:02d}.png'
    scene['image_prompt'] = scene.pop('prompt')

storyboard = {
    'title': 'Chương 12 - Full',
    'aspect_ratio': '9:16',
    'width': 1080,
    'height': 1920,
    'fps': 30,
    'language': 'vi',
    'scenes': scenes,
}
(project / 'storyboard-full.json').write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding='utf-8')
print(project / 'storyboard-full.json')
print(len(scenes))
