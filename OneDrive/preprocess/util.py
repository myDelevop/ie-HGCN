import numpy as np
import scipy.sparse as sp
import scipy.io as sio
import pickle
import torch
from sklearn.feature_extraction.text import HashingVectorizer, TfidfTransformer
from sklearn.manifold import TSNE
from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score
from sklearn.cluster import KMeans
# import matplotlib
# # matplotlib.use('Agg')
# matplotlib.use('TkAgg')
# import matplotlib.pyplot as plt




def kmeans(X, y, n_clusters, repeat=10):
    nmi_list = []
    ari_list = []
    for _ in range(repeat):
        kmeans = KMeans(n_clusters=n_clusters)
        y_pred = kmeans.fit_predict(X)
        nmi_score = normalized_mutual_info_score(y, y_pred, average_method='arithmetic')
        ari_score = adjusted_rand_score(y, y_pred)
        nmi_list.append(nmi_score)
        ari_list.append(ari_score)
    return np.mean(nmi_list), np.std(nmi_list), np.mean(ari_list), np.std(ari_list)



def visual_embd(seed, train_percent, embd, label):
	visual_vec = TSNE(n_components=2).fit_transform(embd)

	# markers = ['o', 'v', 's', 'X']
	# colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
	# fig = plt.figure()
	# ax = fig.add_subplot(111)
	# classes = np.unique(label).tolist()
	# for c_i in classes:
	# 	ax.scatter(visual_vec[label==c_i, 0], visual_vec[label==c_i, 1], c=colors[c_i], marker=markers[c_i], s=10)
	# plt.show()


	fig = plt.figure()
	ax = fig.add_subplot(111)
	ax.scatter(visual_vec[:,0], visual_vec[:,1], c=label, s=3)
	# plt.show()

	# fig_name = './test/visualization/visual_imdb/hgcn_tune/'+'_'+str(train_percent)+'_'+str(seed)+'.pdf'
	# fig_name = './test/visualization/visual_acm/hgcn_tune/'+'_'+str(train_percent)+'_'+str(seed)+'.pdf'
	fig_name = './test/visualization/visual_dblp/hgcn_tune/'+'_'+str(train_percent)+'_'+str(seed)+'.pdf'
	plt.savefig(fig_name)
	plt.close(fig)



def sp_mat_row_normalize(mx):
    """Row-normalize sparse matrix"""
    rowsum = np.array(mx.sum(1))
    r_inv = np.power(rowsum, -1).flatten()
    r_inv[np.isinf(r_inv)] = 0.
    r_mat_inv = sp.diags(r_inv)
    mx = r_mat_inv.dot(mx)
    return mx



def row_normalize(mat):
    """Row-normalize matrix"""
    rowsum = mat.sum(1)
    rowsum[rowsum == 0.] = 0.01
    return mat / rowsum



def sp_coo_2_sp_tensor(sp_coo_mat):
    """Convert a scipy sparse matrix to a torch sparse tensor."""
    indices = torch.from_numpy(np.vstack((sp_coo_mat.row, sp_coo_mat.col)).astype(np.int64))
    values = torch.from_numpy(sp_coo_mat.data)
    shape = torch.Size(sp_coo_mat.shape)
    return torch.sparse.FloatTensor(indices, values, shape)



def accuracy(output, labels):
    preds = output.max(1)[1].type_as(labels)
    correct = preds.eq(labels).double()
    correct = correct.sum()
    return correct / len(labels)



def load_imdb3228(train_percent):
	np.random.seed(0)

	path='./data/imdb10197/'
	dataset='imdb10197'
	print('imdb3228', train_percent)
	
	with open('{}{}_movie_feature.pkl'.format(path, dataset), 'rb') as in_file:
		m_ft = pickle.load(in_file)

	with open('{}{}_sp_adj_mats.pkl'.format(path, dataset), 'rb') as in_file:
		(sp_A_m_a, sp_A_m_c, sp_A_m_d, sp_A_m_t, sp_A_m_u, sp_A_m_g) = pickle.load(in_file)

	A_m_g = sp_A_m_g.toarray()
	A_m_a = sp_A_m_a.tocsr()
	A_m_u = sp_A_m_u.tocsr()
	A_m_d = sp_A_m_d.tocsr()
	
	idx_m = np.where(A_m_g.sum(1)==1)[0]
	idx_g = np.array([4,6,7,10])
	idx_m = idx_m[np.where(A_m_g[idx_m][:,idx_g].sum(1) == 1)[0]]
	
	idx_a = np.where(A_m_a[idx_m].sum(0) > 0)[1]
	idx_u = np.where(A_m_u[idx_m].sum(0) > 0)[1]
	idx_d = np.where(A_m_d[idx_m].sum(0) > 0)[1]

	A_m_a = A_m_a[idx_m][:,idx_a]
	A_m_u = A_m_u[idx_m][:,idx_u]
	A_m_d = A_m_d[idx_m][:,idx_d]
	A_m_g = A_m_g[idx_m][:,idx_g]

	label = {}
	m_label = torch.LongTensor(A_m_g.argmax(1))
	rand_idx = np.random.permutation(m_label.shape[0])
	val_percent =  (1.0 - train_percent)/2
	idx_train_m = torch.LongTensor(rand_idx[int(m_label.shape[0]*0.0): int(m_label.shape[0]*train_percent)])
	idx_val_m = torch.LongTensor(rand_idx[int(m_label.shape[0]*train_percent): int(m_label.shape[0]*(train_percent + val_percent))])
	idx_test_m = torch.LongTensor(rand_idx[int(m_label.shape[0]*(train_percent + val_percent)): int(m_label.shape[0]*1.0)])
	label['m'] = [m_label, idx_train_m, idx_val_m, idx_test_m]

	ft_dict = {}


	m_ft = m_ft[idx_m]
	m_ft_std = (m_ft - m_ft.mean(0)) / m_ft.std(0)
	ft_dict['m'] = torch.FloatTensor(m_ft_std)
	
	# ft_dict['m'] = torch.FloatTensor(A_m_a.shape[0], 128)
	# torch.nn.init.xavier_uniform_(ft_dict['m'].data, gain=1.414)
	
	ft_dict['a'] = torch.FloatTensor(A_m_a.shape[1], 128)
	torch.nn.init.xavier_uniform_(ft_dict['a'].data, gain=1.414)
	ft_dict['u'] = torch.FloatTensor(A_m_u.shape[1], 128)
	torch.nn.init.xavier_uniform_(ft_dict['u'].data, gain=1.414)
	ft_dict['d'] = torch.FloatTensor(A_m_d.shape[1], 128)
	torch.nn.init.xavier_uniform_(ft_dict['d'].data, gain=1.414)


	adj_dict = {'m':{}, 'a':{}, 'u':{}, 'd':{}}
	adj_dict['m']['a'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(A_m_a)))
	adj_dict['m']['u'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(A_m_u)))
	adj_dict['m']['d'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(A_m_d)))
	
	adj_dict['a']['m'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(A_m_a.transpose())))
	adj_dict['u']['m'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(A_m_u.transpose())))
	adj_dict['d']['m'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(A_m_d.transpose())))

	#return label, ft_dict, adj_dict



	# hgcn write
	hgcn_path = './data/imdb3228/imdb3228_hgcn_'+str(train_percent)+'.pkl'
	print('hgcn dump: ', hgcn_path)
	with open(hgcn_path, 'wb') as out_file:
		adj_dict['m']['a'] = adj_dict['m']['a'].to_dense()
		adj_dict['m']['u'] = adj_dict['m']['u'].to_dense()
		adj_dict['m']['d'] = adj_dict['m']['d'].to_dense()
		
		adj_dict['a']['m'] = adj_dict['a']['m'].to_dense()
		adj_dict['u']['m'] = adj_dict['u']['m'].to_dense()
		adj_dict['d']['m'] = adj_dict['d']['m'].to_dense()

		pickle.dump((label, ft_dict, adj_dict), out_file)


	# hgcn load
	hgcn_path = './data/imdb3228/imdb3228_hgcn_'+str(train_percent)+'.pkl'
	print('hgcn load: ', hgcn_path, '\n')
	with open(hgcn_path, 'rb') as in_file:
		(label, ft_dict, adj_dict) = pickle.load(in_file)
		adj_dict['m']['a'] = adj_dict['m']['a'].to_sparse()
		adj_dict['m']['u'] = adj_dict['m']['u'].to_sparse()
		adj_dict['m']['d'] = adj_dict['m']['d'].to_sparse()
		
		adj_dict['a']['m'] = adj_dict['a']['m'].to_sparse()
		adj_dict['u']['m'] = adj_dict['u']['m'].to_sparse()
		adj_dict['d']['m'] = adj_dict['d']['m'].to_sparse()

	#return label, ft_dict, adj_dict


	

	# metapath write
	metapath_path = './data/imdb3228/imdb3228_metapath_'+str(train_percent)+'.pkl'
	print('metapath dump: ', metapath_path)
	with open(metapath_path, 'wb') as out_file:
		label = [A_m_g, idx_train_m.numpy(), idx_val_m.numpy(), idx_test_m.numpy()]
		feature = ft_dict['m'].numpy()
		adj_list = []
		adj_list.append((A_m_a * A_m_a.transpose()).todense())  # MAM
		adj_list.append((A_m_u * A_m_u.transpose()).todense())	# MUM
		adj_list.append((A_m_d * A_m_d.transpose()).todense())	# MDM
		
		pickle.dump((label, feature, adj_list), out_file)


	# metapath load
	metapath_path = './data/imdb3228/imdb3228_metapath_'+str(train_percent)+'.pkl'
	print('metapath load: ', metapath_path)
	with open(metapath_path, 'rb') as in_file:
		(label, feature, adj_list) = pickle.load(in_file)



def load_acm4025(train_percent):
	np.random.seed(0)

	path='./data/acm4025/'
	dataset='acm4025'
	print(path+dataset, train_percent)

	data = sio.loadmat('{}{}.mat'.format(path, dataset))

	label = {}
	p_label = torch.LongTensor(data['p_label'].argmax(1))
	rand_idx = np.random.permutation(p_label.shape[0])
	val_percent =  (1.0 - train_percent)/2
	idx_train_p = torch.LongTensor(rand_idx[int(p_label.shape[0]*0.0): int(p_label.shape[0]*train_percent)])
	idx_val_p = torch.LongTensor(rand_idx[int(p_label.shape[0]*train_percent): int(p_label.shape[0]*(train_percent + val_percent))])
	idx_test_p = torch.LongTensor(rand_idx[int(p_label.shape[0]*(train_percent + val_percent)): int(p_label.shape[0]*1.0)])
	label['p'] = [p_label, idx_train_p, idx_val_p, idx_test_p]


	adj_dict = {'p':{}, 'a':{}, 'l':{}}

	adj_dict['p']['a'] = sp_coo_2_sp_tensor(data['sp_A_p_a'].astype(np.float32).tocoo())
	adj_dict['p']['l'] = sp_coo_2_sp_tensor(data['sp_A_p_l'].astype(np.float32).tocoo())
	
	adj_dict['a']['p'] = sp_coo_2_sp_tensor(data['sp_A_a_p'].astype(np.float32).tocoo())
	adj_dict['l']['p'] = sp_coo_2_sp_tensor(data['sp_A_l_p'].astype(np.float32).tocoo())


	ft_dict = {}

	
	corpus = data['p_ft'].squeeze()
	corpus_str = [corp[0] for corp in corpus]
	vectorizer = HashingVectorizer(n_features=128)
	p_text_ft = vectorizer.fit_transform(corpus_str)
	transformer = TfidfTransformer()
	p_text_ft = transformer.fit_transform(p_text_ft) 
	p_ft = p_text_ft.todense()

	p_ft_std = (p_ft - p_ft.mean(0)) / p_ft.std(0)
	ft_dict['p'] = torch.FloatTensor(p_ft_std)

	ft_dict['a'] = torch.FloatTensor(adj_dict['p']['a'].shape[1], 128)
	torch.nn.init.xavier_uniform_(ft_dict['a'].data, gain=1.414)
	ft_dict['l'] = torch.FloatTensor(adj_dict['p']['l'].shape[1], 128)
	torch.nn.init.xavier_uniform_(ft_dict['l'].data, gain=1.414)

	# return label, ft_dict, adj_dict



	# hgcn write
	hgcn_path = './data/acm4025/acm4025_hgcn_'+str(train_percent)+'.pkl'
	print('hgcn dump: ', hgcn_path)
	with open(hgcn_path, 'wb') as out_file:
		adj_dict['p']['a'] = adj_dict['p']['a'].to_dense()
		adj_dict['p']['l'] = adj_dict['p']['l'].to_dense()
	
		adj_dict['a']['p'] = adj_dict['a']['p'].to_dense()
		adj_dict['l']['p'] = adj_dict['l']['p'].to_dense()

		pickle.dump((label, ft_dict, adj_dict), out_file)



	# hgcn load
	hgcn_path = './data/acm4025/acm4025_hgcn_'+str(train_percent)+'.pkl'
	print('hgcn load: ', hgcn_path, '\n')
	with open(hgcn_path, 'rb') as in_file:
		(label, ft_dict, adj_dict) = pickle.load(in_file)

		adj_dict['p']['a'] = adj_dict['p']['a'].to_sparse()
		adj_dict['p']['l'] = adj_dict['p']['l'].to_sparse()
		
		adj_dict['a']['p'] = adj_dict['a']['p'].to_sparse()
		adj_dict['l']['p'] = adj_dict['l']['p'].to_sparse()
	
	# return label, ft_dict, adj_dict



	# # metapath write
	metapath_path = './data/acm4025/acm4025_metapath_'+str(train_percent)+'.pkl'
	print('metapath dump: ', metapath_path)
	with open(metapath_path, 'wb') as out_file:
		label = [data['p_label'], idx_train_p.numpy(), idx_val_p.numpy(), idx_test_p.numpy()]
		feature = ft_dict['p'].numpy()
		adj_list = []
		adj_list.append((data['sp_A_p_a'] * data['sp_A_a_p']).todense())  # PAP
		adj_list.append((data['sp_A_p_l'] * data['sp_A_l_p']).todense())  # PSP
		
		pickle.dump((label, feature, adj_list), out_file)


	# metapath load
	metapath_path = './data/acm4025/acm4025_metapath_'+str(train_percent)+'.pkl'
	print('metapath load: ', metapath_path)
	with open(metapath_path, 'rb') as in_file:
		(label, feature, adj_list) = pickle.load(in_file)



def load_dblp4area4057(train_percent):
	# np.random.seed(0)
	
	# path='./data/dblp4area14475/'
	# dataset='dblp4area14475'

	# print('dblp4area4057', train_percent)

	# with open('{}{}_label.pkl'.format(path, dataset), 'rb') as in_file:
	# 	(p_label, a_label, c_label) = pickle.load(in_file)

	# with open('{}{}_sp_adj_mats.pkl'.format(path, dataset), 'rb') as in_file:
	# 	(sp_A_p_a, sp_A_p_c, sp_A_p_t) = pickle.load(in_file)


	# A_p_a = sp_A_p_a.tocsr()
	# A_p_c = sp_A_p_c.tocsr()
	# A_p_t = sp_A_p_t.tocsr()
	
	# idx_a = np.where(a_label != -1)[0]
	# idx_p = np.where(A_p_a[:,idx_a].sum(1) > 0)[0]
	# idx_c = np.where(A_p_c[idx_p].sum(0) > 0)[1]
	# idx_t = np.where(A_p_t[idx_p].sum(0) > 0)[1]

	# A_p_a = A_p_a[idx_p][:,idx_a]
	# A_p_c = A_p_c[idx_p][:,idx_c]
	# A_p_t = A_p_t[idx_p][:,idx_t]

	# p_label = p_label[idx_p]
	# a_label = a_label[idx_a]
	# c_label = c_label[idx_c]


	# # label and dataset split idx
	# label = {}
	# val_percent =  (1.0 - train_percent)/2
		
	# label_index_p = np.where(p_label != -1)[0]
	# p_label = torch.LongTensor(p_label)
	# np.random.shuffle(label_index_p)
	# idx_train_p = torch.LongTensor(label_index_p[0: int(len(label_index_p)*train_percent)])
	# idx_val_p = torch.LongTensor(label_index_p[int(len(label_index_p)*train_percent): int(len(label_index_p)*(train_percent + val_percent))])
	# idx_test_p = torch.LongTensor(label_index_p[int(len(label_index_p)*(train_percent + val_percent)): ])
	# label['p'] = [p_label, idx_train_p, idx_val_p, idx_test_p]

	# label_index_a = np.where(a_label != -1)[0]
	# a_label = torch.LongTensor(a_label)
	# np.random.shuffle(label_index_a)
	# idx_train_a = torch.LongTensor(label_index_a[0: int(len(label_index_a)*train_percent)])
	# idx_val_a = torch.LongTensor(label_index_a[int(len(label_index_a)*train_percent): int(len(label_index_a)*(train_percent + val_percent))])
	# idx_test_a = torch.LongTensor(label_index_a[int(len(label_index_a)*(train_percent + val_percent)): ])
	# label['a'] = [a_label, idx_train_a, idx_val_a, idx_test_a]

	# label_index_c = np.where(c_label != -1)[0]
	# c_label = torch.LongTensor(c_label)
	# np.random.shuffle(label_index_c)
	# idx_train_c = torch.LongTensor(label_index_c[0: int(len(label_index_c)*train_percent)])
	# idx_val_c = torch.LongTensor(label_index_c[int(len(label_index_c)*train_percent): int(len(label_index_c)*(train_percent + val_percent))])
	# idx_test_c = torch.LongTensor(label_index_c[int(len(label_index_c)*(train_percent + val_percent)): ])
	# label['c'] = [c_label, idx_train_c, idx_val_c, idx_test_c]


	# # features are genreted by xavier_uniform distribution
	# ft_dict = {}
	
	# ft_dict['p'] = torch.FloatTensor(A_p_a.shape[0], 2**7)
	# torch.nn.init.xavier_uniform_(ft_dict['p'].data, gain=1.414)
	# ft_dict['a'] = torch.FloatTensor(A_p_a.shape[1], 2**7)
	# torch.nn.init.xavier_uniform_(ft_dict['a'].data, gain=1.414)
	# ft_dict['c'] = torch.FloatTensor(A_p_c.shape[1], 2**7)
	# torch.nn.init.xavier_uniform_(ft_dict['c'].data, gain=1.414)
	# ft_dict['t'] = torch.FloatTensor(A_p_t.shape[1], 2**7)
	# torch.nn.init.xavier_uniform_(ft_dict['t'].data, gain=1.414)
	

	# # sparse adj mats
	# adj_dict = {'p':{}, 'a':{}, 'c':{}, 't':{}}
	# adj_dict['p']['a'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(A_p_a.todense())))
	# adj_dict['p']['c'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(A_p_c.todense())))
	# adj_dict['p']['t'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(A_p_t.todense())))
	
	# adj_dict['a']['p'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(A_p_a.todense().transpose())))
	# adj_dict['c']['p'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(A_p_c.todense().transpose())))
	# adj_dict['t']['p'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(A_p_t.todense().transpose())))

	# return label, ft_dict, adj_dict



	# # hgcn write
	# hgcn_path = './data/dblp4area4057/dblp4area4057_hgcn_'+str(train_percent)+'.pkl'
	# print('hgcn dump: ', hgcn_path)
	# with open(hgcn_path, 'wb') as out_file:
	# 	adj_dict['p']['a'] = adj_dict['p']['a'].to_dense()
	# 	adj_dict['p']['c'] = adj_dict['p']['c'].to_dense()
	# 	adj_dict['p']['t'] = adj_dict['p']['t'].to_dense()
		
	# 	adj_dict['a']['p'] = adj_dict['a']['p'].to_dense()
	# 	adj_dict['c']['p'] = adj_dict['c']['p'].to_dense()
	# 	adj_dict['t']['p'] = adj_dict['t']['p'].to_dense()

	# 	pickle.dump((label, ft_dict, adj_dict), out_file)



	# hgcn load
	hgcn_path = './data/dblp4area4057/dblp4area4057_hgcn_'+str(train_percent)+'.pkl'
	print('hgcn load: ', hgcn_path, '\n')
	with open(hgcn_path, 'rb') as in_file:
		(label, ft_dict, adj_dict) = pickle.load(in_file)
	
		adj_dict['p']['a'] = adj_dict['p']['a'].to_sparse()
		adj_dict['p']['c'] = adj_dict['p']['c'].to_sparse()
		adj_dict['p']['t'] = adj_dict['p']['t'].to_sparse()
		
		adj_dict['a']['p'] = adj_dict['a']['p'].to_sparse()
		adj_dict['c']['p'] = adj_dict['c']['p'].to_sparse()
		adj_dict['t']['p'] = adj_dict['t']['p'].to_sparse()

	return label, ft_dict, adj_dict



	# metapath write HAN
	# np.random.seed(0)
	# data = sio.loadmat('D:/python3/HAN/data/dblp/DBLP4057.mat')
	
	# val_percent =  (1.0 - train_percent)/2
	# a_label  = data['label']
	# a_idx = np.arange(a_label.shape[0])
	# np.random.shuffle(a_idx)
	# train_idx = a_idx[0: int(a_label.shape[0]*train_percent)]
	# val_idx = a_idx[int(a_label.shape[0]*train_percent): int(a_label.shape[0]*(train_percent + val_percent))]
	# test_idx = a_idx[int(a_label.shape[0]*(train_percent + val_percent)): ]
	
	# # a_label  = data['label']
	# # train_idx = data['train_idx'].squeeze()
	# # val_idx = data['val_idx'].squeeze()
	# # test_idx = data['test_idx'].squeeze()

	# label = [a_label, train_idx, val_idx, test_idx]
	
	# feature = data['features'].astype(np.float32)
	# adj_list = [np.mat(data['net_APA'], dtype=np.float32), np.mat(data['net_APTPA'], dtype=np.float32), np.mat(data['net_APCPA'], dtype=np.float32)]
	# metapath_path = './data/dblp4area4057/dblp4area4057_metapath_'+str(train_percent)+'.pkl'
	# print('metapath dump: ', metapath_path)
	# with open(metapath_path, 'wb') as out_file:
	# 	pickle.dump((label, feature, adj_list), out_file)


	# # metapath write HGCN
	# def encode_onehot(labels):
	#     classes = set(np.unique(labels))
	#     classes_dict = {c: np.identity(len(classes))[i, :] for i, c in enumerate(classes)}
	#     labels_onehot = np.array(list(map(classes_dict.get, labels.tolist())), dtype=np.int32)
	#     return labels_onehot

	# metapath_path = './data/dblp4area4057/dblp4area4057_metapath_'+str(train_percent)+'.pkl'
	# print('metapath dump: ', metapath_path)
	# with open(metapath_path, 'wb') as out_file:
	# 	a_label_one_hot = encode_onehot(a_label)
	# 	label = [a_label_one_hot, idx_train_a.numpy(), idx_val_a.numpy(), idx_test_a.numpy()]
	# 	feature = ft_dict['a'].numpy()
	# 	adj_list = []
	# 	adj_list.append((A_p_a.transpose() * A_p_a).todense())  # APA
	# 	adj_list.append((A_p_a.transpose() * A_p_t * A_p_t.transpose() * A_p_a).todense())  # APTPA
	# 	adj_list.append((A_p_a.transpose() * A_p_c * A_p_c.transpose() * A_p_a).todense())  # APVPA
	# 	pickle.dump((label, feature, adj_list), out_file)



	# # metapath load
	# metapath_path = './data/dblp4area4057/dblp4area4057_metapath_'+str(train_percent)+'.pkl'
	# print('metapath load: ', metapath_path)
	# with open(metapath_path, 'rb') as in_file:
	# 	(label, feature, adj_list) = pickle.load(in_file)
	# print('ok')



def load_dblp4area14475(train_percent, author_num=14475):
	# np.random.seed(0)

	# path='./data/dblp4area14475/'
	# dataset='dblp4area14475'

	# print(path+dataset, train_percent)

	# # with open('{}{}_paper_feature.pkl'.format(path, dataset), 'rb') as in_file:
	# # 	p_ft = pickle.load(in_file)

	# with open('{}{}_label.pkl'.format(path, dataset), 'rb') as in_file:
	# 	(p_label, a_label, c_label) = pickle.load(in_file)

	# with open('{}{}_sp_adj_mats.pkl'.format(path, dataset), 'rb') as in_file:
	# 	(sp_A_p_a, sp_A_p_c, sp_A_p_t) = pickle.load(in_file)

	# with open('./data/clean/dblp4area/dump/dblp4area_ids_map_dict.pkl', 'rb') as in_file:
	# 	(p_id_raw2int, a_id_raw2int, c_id_raw2int, t_id_raw2int) = pickle.load(in_file)



	# ''' Test scalability begin'''
	# # A_p_a = sp_A_p_a.tocsr()
	# # A_p_c = sp_A_p_c.tocsr()
	# # A_p_t = sp_A_p_t.tocsr()

	# # idx_a = np.random.permutation(A_p_a.shape[1])[:author_num]
	# # idx_p = np.where(A_p_a[:,idx_a].sum(1) > 0)[0]
	# # idx_c = np.where(A_p_c[idx_p].sum(0) > 0)[1]
	# # idx_t = np.where(A_p_t[idx_p].sum(0) > 0)[1]

	# # A_p_a = A_p_a[idx_p][:,idx_a]
	# # A_p_c = A_p_c[idx_p][:,idx_c]
	# # A_p_t = A_p_t[idx_p][:,idx_t]
	# # print('Number of authors:', A_p_a.shape[1])
	# # # print('Number of papers :', A_p_a.shape[0])
	# # # print('Number of confs  :', A_p_c.shape[1])
	# # # print('Number of terms  :', A_p_t.shape[1])
	# # print('Total Objects: ', A_p_a.shape[1] + A_p_a.shape[0] + A_p_c.shape[1] + A_p_t.shape[1])
	
	# # # print('Number of P-A links  :', A_p_a.nnz)
	# # # print('Number of P-C links  :', A_p_c.nnz)
	# # # print('Number of P-T links  :', A_p_t.nnz)
	# # print('Total Links: ', A_p_a.nnz+ A_p_c.nnz + A_p_t.nnz)

	# # sp_A_p_a = A_p_a.tocoo()
	# # sp_A_p_c = A_p_c.tocoo()
	# # sp_A_p_t = A_p_t.tocoo()

	# # p_label = p_label[idx_p]
	# # a_label = a_label[idx_a]
	# # c_label = c_label[idx_c]
	# ''' Test scalability end'''



	# # label and dataset split idx
	# label = {}
	# val_percent =  (1.0 - train_percent)/2
	
	# label_index_p = np.where(p_label != -1)[0]
	# p_label = torch.LongTensor(p_label)
	# np.random.shuffle(label_index_p)
	# idx_train_p = torch.LongTensor(label_index_p[0: int(len(label_index_p)*train_percent)])
	# idx_val_p = torch.LongTensor(label_index_p[int(len(label_index_p)*train_percent): int(len(label_index_p)*(train_percent + val_percent))])
	# idx_test_p = torch.LongTensor(label_index_p[int(len(label_index_p)*(train_percent + val_percent)): ])
	# label['p'] = [p_label, idx_train_p, idx_val_p, idx_test_p]

	# label_index_a = np.where(a_label != -1)[0]
	# a_label = torch.LongTensor(a_label)
	# np.random.shuffle(label_index_a)
	# idx_train_a = torch.LongTensor(label_index_a[0: int(len(label_index_a)*train_percent)])
	# idx_val_a = torch.LongTensor(label_index_a[int(len(label_index_a)*train_percent): int(len(label_index_a)*(train_percent + val_percent))])
	# idx_test_a = torch.LongTensor(label_index_a[int(len(label_index_a)*(train_percent + val_percent)): ])
	# label['a'] = [a_label, idx_train_a, idx_val_a, idx_test_a]


	# label_index_c = np.where(c_label != -1)[0]
	# c_label = torch.LongTensor(c_label)
	# np.random.shuffle(label_index_c)
	# idx_train_c = torch.LongTensor(label_index_c[0: int(len(label_index_c)*train_percent)])
	# idx_val_c = torch.LongTensor(label_index_c[int(len(label_index_c)*train_percent): int(len(label_index_c)*(train_percent + val_percent))])
	# idx_test_c = torch.LongTensor(label_index_c[int(len(label_index_c)*(train_percent + val_percent)): ])
	# label['c'] = [c_label, idx_train_c, idx_val_c, idx_test_c]


	# # feature: paper feature is loaded, other features are genreted by xavier_uniform distribution
	# ft_dict = {}
	

	# # p_ft_std = (p_ft - p_ft.mean(0)) / p_ft.std(0)
	# # ft_dict['p'] = torch.FloatTensor(p_ft_std)
	
	# ft_dict['p'] = torch.FloatTensor(sp_A_p_a.shape[0], 2**7)
	# torch.nn.init.xavier_uniform_(ft_dict['p'].data, gain=1.414)
	# ft_dict['a'] = torch.FloatTensor(sp_A_p_a.shape[1], 2**7)
	# torch.nn.init.xavier_uniform_(ft_dict['a'].data, gain=1.414)
	# ft_dict['c'] = torch.FloatTensor(sp_A_p_c.shape[1], 2**7)
	# torch.nn.init.xavier_uniform_(ft_dict['c'].data, gain=1.414)
	# ft_dict['t'] = torch.FloatTensor(sp_A_p_t.shape[1], 2**7)
	# torch.nn.init.xavier_uniform_(ft_dict['t'].data, gain=1.414)
	

	# # sparse adj mats
	# adj_dict = {'p':{}, 'a':{}, 'c':{}, 't':{}}
	# adj_dict['p']['a'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(sp_A_p_a.todense())))
	# adj_dict['p']['c'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(sp_A_p_c.todense())))
	# adj_dict['p']['t'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(sp_A_p_t.todense())))
	
	# adj_dict['a']['p'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(sp_A_p_a.todense().transpose())))
	# adj_dict['c']['p'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(sp_A_p_c.todense().transpose())))
	# adj_dict['t']['p'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(sp_A_p_t.todense().transpose())))


	# return label, ft_dict, adj_dict



	# hgcn write
	# hgcn_path = './data/dblp4area14475/dblp4area14475_hgcn_'+str(train_percent)+'.pkl'
	# print('hgcn dump: ', hgcn_path)
	# with open(hgcn_path, 'wb') as out_file:
	# 	adj_dict['p']['a'] = adj_dict['p']['a'].to_dense()
	# 	adj_dict['p']['c'] = adj_dict['p']['c'].to_dense()
	# 	adj_dict['p']['t'] = adj_dict['p']['t'].to_dense()
		
	# 	adj_dict['a']['p'] = adj_dict['a']['p'].to_dense()
	# 	adj_dict['c']['p'] = adj_dict['c']['p'].to_dense()
	# 	adj_dict['t']['p'] = adj_dict['t']['p'].to_dense()

		# pickle.dump((label, ft_dict, adj_dict), out_file)



	# hgcn load
	hgcn_path = './data/dblp4area14475/training_percent/dblp4area14475_hgcn_'+str(train_percent)+'.pkl'
	print('hgcn load: ', hgcn_path, '\n')
	with open(hgcn_path, 'rb') as in_file:
		(label, ft_dict, adj_dict) = pickle.load(in_file)
	
		adj_dict['p']['a'] = adj_dict['p']['a'].to_sparse()
		adj_dict['p']['c'] = adj_dict['p']['c'].to_sparse()
		adj_dict['p']['t'] = adj_dict['p']['t'].to_sparse()
		
		adj_dict['a']['p'] = adj_dict['a']['p'].to_sparse()
		adj_dict['c']['p'] = adj_dict['c']['p'].to_sparse()
		adj_dict['t']['p'] = adj_dict['t']['p'].to_sparse()

	return label, ft_dict, adj_dict


	# metapath write
	# metapath_path = './data/dblp4area14475/dblp4area14475_metapath_'+str(train_percent)+'.pkl'
	# metapath_path = './data/dblp4area14475/dblp4area14475_metapath_'+str(author_num)+'_'+str(train_percent)+'.pkl'
	# print('metapath dump: ', metapath_path)

	# def encode_onehot_dblp4area14475(labels):
	#     classes = set(np.unique(labels)[1:])
	#     classes_dict = {c: np.identity(len(classes), dtype=np.int32)[i, :] for i, c in enumerate(classes)}
	#     classes_dict[-1] = np.zeros(len(classes), dtype=np.int32)
	#     labels_onehot = np.array(list(map(classes_dict.get, labels.tolist())), dtype=np.int32)
	#     return labels_onehot



	# with open(metapath_path, 'wb') as out_file:
	# 	a_label_one_hot = encode_onehot_dblp4area14475(a_label)
	# 	label = [a_label_one_hot, idx_train_a.numpy(), idx_val_a.numpy(), idx_test_a.numpy()]
	# 	feature = ft_dict['a'].numpy()
	# 	adj_list = []
	# 	adj_list.append((sp_A_p_a.transpose() * sp_A_p_a).todense())  # APA
	# 	adj_list.append((sp_A_p_a.transpose() * sp_A_p_t * sp_A_p_t.transpose() * sp_A_p_a).todense())  # APTPA
	# 	adj_list.append((sp_A_p_a.transpose() * sp_A_p_c * sp_A_p_c.transpose() * sp_A_p_a).todense())  # APVPA
		
	# 	pickle.dump((label, feature, adj_list), out_file)



	# metapath load
	# metapath_path = './data/dblp4area14475/dblp4area14475_metapath_'+str(train_percent)+'.pkl'
	# print('metapath load: ', metapath_path)
	# with open(metapath_path, 'rb') as in_file:
	# 	(label, feature, adj_list) = pickle.load(in_file)
	



def load_imdb128():
	path='./data/imdb128/'
	dataset='imdb128'
	print('Loading {} dataset...'.format(dataset))

	with open('{}{}_movie_feature.pkl'.format(path, dataset), 'rb') as in_file:
		m_ft = pickle.load(in_file)

	with open('{}{}_sp_adj_mats.pkl'.format(path, dataset), 'rb') as in_file:
		(sp_A_m_a, sp_A_m_c, sp_A_m_d, sp_A_m_t, sp_A_m_u, sp_A_m_g) = pickle.load(in_file)


	# label: genre
	label = {}
	m_label = sp_A_m_g.todense()
	m_label = torch.LongTensor(m_label)
	idx_train_m = torch.LongTensor(np.arange(0, int(m_label.shape[0]*0.8)))
	idx_val_m = torch.LongTensor(np.arange(int(m_label.shape[0]*0.8), int(m_label.shape[0]*0.9)))
	idx_test_m = torch.LongTensor(np.arange(int(m_label.shape[0]*0.9), m_label.shape[0]))
	label['m'] = [m_label, idx_train_m, idx_val_m, idx_test_m]


	# feature: movie feature is loaded, other features are genreted by their one-hot vectors
	ft_dict = {}
	m_ft_std = (m_ft - m_ft.mean(0)) / m_ft.std(0)
	ft_dict['m'] = torch.FloatTensor(m_ft_std)
	
	ft_dict['a'] = torch.FloatTensor(np.mat(np.eye((sp_A_m_a.shape[1]))))
	ft_dict['u'] = torch.FloatTensor(np.mat(np.eye((sp_A_m_u.shape[1]))))
	ft_dict['t'] = torch.FloatTensor(np.mat(np.eye((sp_A_m_t.shape[1]))))
	ft_dict['c'] = torch.FloatTensor(np.mat(np.eye((sp_A_m_c.shape[1]))))
	ft_dict['d'] = torch.FloatTensor(np.mat(np.eye((sp_A_m_d.shape[1]))))


	# dense adj mats
	adj_dict = {'m':{}, 'a':{}, 'u':{}, 't':{}, 'c':{}, 'd':{}}
	adj_dict['m']['a'] = torch.FloatTensor(row_normalize(sp_A_m_a.todense()))
	adj_dict['m']['u'] = torch.FloatTensor(row_normalize(sp_A_m_u.todense()))
	adj_dict['m']['t'] = torch.FloatTensor(row_normalize(sp_A_m_t.todense()))
	adj_dict['m']['c'] = torch.FloatTensor(row_normalize(sp_A_m_c.todense()))
	adj_dict['m']['d'] = torch.FloatTensor(row_normalize(sp_A_m_d.todense()))
	
	adj_dict['a']['m'] = torch.FloatTensor(row_normalize(sp_A_m_a.todense().transpose()))
	adj_dict['u']['m'] = torch.FloatTensor(row_normalize(sp_A_m_u.todense().transpose()))
	adj_dict['t']['m'] = torch.FloatTensor(row_normalize(sp_A_m_t.todense().transpose()))
	adj_dict['c']['m'] = torch.FloatTensor(row_normalize(sp_A_m_c.todense().transpose()))
	adj_dict['d']['m'] = torch.FloatTensor(row_normalize(sp_A_m_d.todense().transpose()))


	return label, ft_dict, adj_dict


def load_imdb10197():
	path='./data/imdb10197/'
	dataset='imdb10197'
	print('Loading {} dataset...'.format(dataset))

	with open('{}{}_movie_feature.pkl'.format(path, dataset), 'rb') as in_file:
		m_ft = pickle.load(in_file)

	with open('{}{}_sp_adj_mats.pkl'.format(path, dataset), 'rb') as in_file:
		(sp_A_m_a, sp_A_m_c, sp_A_m_d, sp_A_m_t, sp_A_m_u, sp_A_m_g) = pickle.load(in_file)


	# label: genre
	label = {}
	m_label = sp_A_m_g.todense()
	m_label = np.delete(m_label, -4, 1)


	m_label = torch.LongTensor(m_label)   # multi label indicator
	
	rand_idx = np.random.permutation(m_label.shape[0])
	idx_7592 = np.where(rand_idx == 7592)[0]
	rand_idx = np.delete(rand_idx, idx_7592[0], 0)
	idx_train_m = torch.LongTensor(rand_idx[int(m_label.shape[0]*0.0): int(m_label.shape[0]*0.6)])
	idx_val_m = torch.LongTensor(rand_idx[int(m_label.shape[0]*0.6): int(m_label.shape[0]*0.8)])
	idx_test_m = torch.LongTensor(rand_idx[int(m_label.shape[0]*0.8): int(m_label.shape[0]*1.0)])

	label['m'] = [m_label, idx_train_m, idx_val_m, idx_test_m]

	# feature: movie feature is loaded, other features are genreted by xavier_uniform distribution
	ft_dict = {}
	m_ft_std = (m_ft - m_ft.mean(0)) / m_ft.std(0)
	ft_dict['m'] = torch.FloatTensor(m_ft_std)
	
	ft_dict['a'] = torch.FloatTensor(sp_A_m_a.shape[1], 256)
	torch.nn.init.xavier_uniform_(ft_dict['a'].data, gain=1.414)
	ft_dict['u'] = torch.FloatTensor(sp_A_m_u.shape[1], 256)
	torch.nn.init.xavier_uniform_(ft_dict['u'].data, gain=1.414)
	ft_dict['d'] = torch.FloatTensor(sp_A_m_d.shape[1], 256)
	torch.nn.init.xavier_uniform_(ft_dict['d'].data, gain=1.414)
	

	# sparse adj mats
	adj_dict = {'m':{}, 'a':{}, 'u':{}, 'd':{}}
	adj_dict['m']['a'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(sp_A_m_a.todense())))
	adj_dict['m']['u'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(sp_A_m_u.todense())))
	adj_dict['m']['d'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(sp_A_m_d.todense())))
	
	adj_dict['a']['m'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(sp_A_m_a.todense().transpose())))
	adj_dict['u']['m'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(sp_A_m_u.todense().transpose())))
	adj_dict['d']['m'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(sp_A_m_d.todense().transpose())))


	# dataset split mask
	return label, ft_dict, adj_dict


def load_dbis():
	path='./data/dbis/'
	dataset='dbis'
	print('Loading {} dataset...'.format(dataset))

	with open('{}{}_paper_feature.pkl'.format(path, dataset), 'rb') as in_file:
		p_ft = pickle.load(in_file)

	with open('{}{}_author_label.pkl'.format(path, dataset), 'rb') as in_file:
		author_label = np.array(pickle.load(in_file), dtype=np.int64)
		author_label[:,1] = author_label[:,1] - 1

	norm_adj_mats = sio.loadmat('{}{}_sp_row_norm_adj_mats.mat'.format(path, dataset))


	# author label
	label = {}

	a_label = np.full(norm_adj_mats['norm_p_a'].shape[1], -1, dtype=np.int64)
	a_label[author_label[:,0]] = author_label[:,1]
	a_label = torch.LongTensor(a_label)

	# idx_train_a = torch.LongTensor(author_label[:,0][int(author_label.shape[0]*0): int(author_label.shape[0]*0.8)])
	# idx_val_a = torch.LongTensor(author_label[:,0][int(author_label.shape[0]*0.8): int(author_label.shape[0]*0.9)])
	# idx_test_a = torch.LongTensor(author_label[:,0][int(author_label.shape[0]*0.9): int(author_label.shape[0]*1)])

	idx_train_a = []
	np.random.shuffle(author_label)

	# author_label_train = author_label[int(author_label.shape[0]*0.0):int(author_label.shape[0]*0.8)]
	# cate_num = np.unique(author_label_train[:,1]).shape[0]
	# if cate_num == 8:
	# 	max_cate_num = np.bincount(author_label_train[:,1]).max()
	# 	for cate_i in range(cate_num):
	# 		cate_i_idx = author_label_train[np.where(author_label_train[:,1]==cate_i)[0], 0]
	# 		idx_train_a.extend(cate_i_idx[:max_cate_num])
	# 	np.random.shuffle(idx_train_a)
	# 	idx_train_a = torch.LongTensor(idx_train_a)
	# else:
	# 	print('please check the train label distribution!')
	# 	exit()

	idx_train_a = torch.LongTensor(author_label[int(author_label.shape[0]*0.0):int(author_label.shape[0]*0.8), 0])
	idx_val_a = torch.LongTensor(author_label[int(author_label.shape[0]*0.8):int(author_label.shape[0]*0.9), 0])
	idx_test_a = torch.LongTensor(author_label[int(author_label.shape[0]*0.9):int(author_label.shape[0]*1.0), 0])




	label['a'] = [a_label, idx_train_a, idx_val_a, idx_test_a]
	
	# feature: paper feature is loaded, other features are genreted by xavier_uniform distribution
	ft_dict = {}
	p_ft_std = (p_ft - p_ft.mean(0)) / p_ft.std(0)
	ft_dict['p'] = torch.FloatTensor(p_ft_std)
	
		
	ft_dict['a'] = torch.FloatTensor(norm_adj_mats['norm_p_a'].shape[1], 128)
	torch.nn.init.xavier_uniform_(ft_dict['a'].data, gain=1.414)
	ft_dict['c'] = torch.FloatTensor(norm_adj_mats['norm_p_c'].shape[1], 128)
	torch.nn.init.xavier_uniform_(ft_dict['c'].data, gain=1.414)
	

	# sparse adj mats
	adj_dict = {'p':{}, 'a':{}, 'c':{}}

	# adj_dict['p']['a'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(sp_A_p_a.todense())))
	# adj_dict['p']['c'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(sp_A_p_c.todense())))
	
	# adj_dict['a']['p'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(sp_A_p_a.todense().transpose())))
	# adj_dict['c']['p'] = sp_coo_2_sp_tensor(sp.coo_matrix(row_normalize(sp_A_p_c.todense().transpose())))

	adj_dict['p']['a'] = sp_coo_2_sp_tensor(norm_adj_mats['norm_p_a'].astype(np.float32).tocoo())
	adj_dict['p']['c'] = sp_coo_2_sp_tensor(norm_adj_mats['norm_p_c'].astype(np.float32).tocoo())
	
	adj_dict['a']['p'] = sp_coo_2_sp_tensor(norm_adj_mats['norm_a_p'].astype(np.float32).tocoo())
	adj_dict['c']['p'] = sp_coo_2_sp_tensor(norm_adj_mats['norm_c_p'].astype(np.float32).tocoo())


	return label, ft_dict, adj_dict


def load_douban1594():
	path='./data/douban1594/'
	dataset='douban1594'
	print('Loading {} dataset...'.format(dataset))

	data = sio.loadmat('{}{}.mat'.format(path, dataset))


	label = {}
	m_label = torch.LongTensor(data['A_m_t'].argmax(1))
	rand_idx = np.random.permutation(m_label.shape[0])
	idx_train_m = torch.LongTensor(rand_idx[int(m_label.shape[0]*0.0): int(m_label.shape[0]*0.8)])
	idx_val_m = torch.LongTensor(rand_idx[int(m_label.shape[0]*0.8): int(m_label.shape[0]*0.9)])
	idx_test_m = torch.LongTensor(rand_idx[int(m_label.shape[0]*0.9): int(m_label.shape[0]*1.0)])
	label['m'] = [m_label, idx_train_m, idx_val_m, idx_test_m]


	adj_dict = {'m':{}, 'a':{}, 'd':{}}

	adj_dict['m']['a'] = sp_coo_2_sp_tensor(data['sp_A_m_a'].astype(np.float32).tocoo())
	adj_dict['m']['d'] = sp_coo_2_sp_tensor(data['sp_A_m_d'].astype(np.float32).tocoo())
	
	adj_dict['a']['m'] = sp_coo_2_sp_tensor(data['sp_A_a_m'].astype(np.float32).tocoo())
	adj_dict['d']['m'] = sp_coo_2_sp_tensor(data['sp_A_d_m'].astype(np.float32).tocoo())


	ft_dict = {}
	
	
	ft_dict['m'] = torch.FloatTensor(adj_dict['m']['a'].shape[0], 128)
	torch.nn.init.xavier_uniform_(ft_dict['m'].data, gain=1.414)
	ft_dict['a'] = torch.FloatTensor(adj_dict['m']['a'].shape[1], 128)
	torch.nn.init.xavier_uniform_(ft_dict['a'].data, gain=1.414)
	ft_dict['d'] = torch.FloatTensor(adj_dict['m']['d'].shape[1], 128)
	torch.nn.init.xavier_uniform_(ft_dict['d'].data, gain=1.414)

	return label, ft_dict, adj_dict



if __name__ == '__main__':
	load_imdb3228(0.2)	
	load_imdb3228(0.4)	
	load_imdb3228(0.6)	
	load_imdb3228(0.8)	
	load_acm4025(0.2)
	# load_acm4025(0.4)
	# load_acm4025(0.6)
	# load_acm4025(0.8)
	# load_dblp4area4057(0.2)
	# load_dblp4area4057(0.4)
	# load_dblp4area4057(0.6)
	# load_dblp4area4057(0.8)
	# load_dblp4area14475(0.2)
	# load_dblp4area14475(0.4)
	# load_dblp4area14475(0.6)
	# load_dblp4area14475(0.8)
	# load_odbmdb()


	# load_imdb128()
	# load_imdb10197()
	# load_dbis()
	# load_douban1594()