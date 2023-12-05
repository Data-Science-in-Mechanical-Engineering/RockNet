%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

1;

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

function pT = gen1(K, N)

%	pT = rand(1, K);
	pT = 0.5 * ones(1, K);

	pT(1) = 1;		% myself (hides all others in case of Tx, detected for sure)

	p = zeros(N, length(pT));

	for i = 1 : 100

%		i, fflush(stdout);

		for k = 1 : length(pT)
			p(:,k) = 1 - pT(k) * (1 - pT(k)) .^ [0 : rows(p) - 1]';
		endfor

		for k2 = 2 : length(pT)
			x = prod(p(:, setdiff([1:K], k2)), 2) .* (1 - pT(k2)) .^ [-1 : rows(p) - 2]';
			pT(k2) = sum(x) / sum(x .* [1 : rows(p)]');
		endfor

		if (max(pT(2:end)) - min(pT) < 0.001)
			break;
		endif

	endfor

endfunction

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

function pT = gen2(K, N, pmax = 0.5)

	pT = zeros(1, K);

	k = 1;
	for n = 2 : N

		printf("\rgen2: %3u%% done (%u / %u)", round(n / N * 100), n, N); fflush(stdout);
		
		pT2 = gen1(K, n);
		pT(k:end) = pT2(k:end);

		p = 1 - pT .* ((1 - pT) .^ (n - 1));
		p = cumprod(p);

		k = find(p < pmax, 1) + 1;

	endfor

	printf("\n");

endfunction

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

function plot1(pT, Nmax, Nmean)

	p = zeros(Nmax, length(pT));
	for k = 1 : length(pT)
		p(:,k) = 1 - pT(k) * (1 - pT(k)) .^ [0 : rows(p) - 1]';
	endfor
	p = cumprod(p, 2);

	clf();
	subplot(2,2,1);
	plot(pT);
	ylim([-0.05, 1.05]);
	grid on;
	subplot(2,2,3:4);
	h = plot(p'); 
	set(h(Nmean), "linewidth", 3);
	grid on;
	subplot(2,2,2);
	plot(sum(p, 1));
	ylim([-0.05, Nmax]);
	grid on;

endfunction

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
if 0

	Nmax = 5;
	Nmean = min(max(10, round(Nmax ^ 0.7)), Nmax);
%	Nmean = min(max(16, round(Nmax / 4)), Nmax);
	K = min(5 * Nmax, 256);

	pT = gen1(K, Nmean);
	figure(0 + Nmean);
	set(gcf(), "name", sprintf("Nmax = %u, Nmean = %u", Nmax, Nmean));
	plot1(pT, Nmax, Nmean);

	pT2 = max(pT, 1 ./ (1 : K));
	figure(1000 + Nmean);
	set(gcf(), "name", sprintf("Nmax = %u, Nmean = %u", Nmax, Nmean));
	plot1(pT2, Nmax, Nmean);

	pT2 = max(pT, 1 ./ (2 .^ ceil(log2(1 : K))));
	figure(2000 + Nmean);
	set(gcf(), "name", sprintf("Nmax = %u, Nmean = %u", Nmax, Nmean));
	plot1(pT2, Nmax, Nmean);

	pT2 = max(pT(end), 1 - 0.25 * (0 : K - 1));
%	pT2 = max(pT, 1 ./ (2 .^ round(log2(1 : K))));
	figure(3000 + Nmean);
	set(gcf(), "name", sprintf("Nmax = %u, Nmean = %u", Nmax, Nmean));
	plot1(pT2, Nmax, Nmean);

	pmax = 0.7;
	pT = gen2(K, Nmax, pmax);
	figure(4000 + Nmax);
	set(gcf(), "name", sprintf("Nmax = %u, pmax = %f", Nmax, pmax));
	plot1(pT, Nmax, Nmean);

%	pT = repmat(1 / N, 1, K);
%	pT = 1 ./ (1 : K);
	%pT = 1 ./ sqrt(1 : K);
	%pT = 1 ./ (1 : K) .^ 2;
	%pT = 0.5 .^ linspace(0, 16, K + 1);

	%pT(2:end) .*= 0.5;
%	pT = max(pT, 0.083367);
	%pT(2:end) = min(pT(2:end), 1 / 16);
%	I = find(pT > 1 / N);
%	pT(I) = max(pT(I) / 2, 1 / N);

endif
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
if 1

	Nmax = 256;
	ptest = 1/3;

	lut_name = "MX_DISCOVERY_EXIT_SLOT_LUT";
	p_name = "MX_DISCOVERY_PTX";

	data = cell(Nmax, 1);

	for N = 2 : Nmax

		printf("\r %3u%% done (%u / %u)", round(N / Nmax * 100), N, Nmax); fflush(stdout);

		Nmean = min(max(10, round(N ^ 0.7)), N);
		K = max(5 * Nmean, 2 * N);	% range evaluated for optimization

		pT = gen1(K, Nmean);
		pT = max(pT(end), 1 - 0.25 * (0 : K - 1));
%		pT = max(pT(end), 1 ./ (2 .^ ceil(log2(1 : K))));

%		figure(Nmean);
%		set(gcf(), "name", sprintf("N = %u, Nmean = %u, K = %u", N, Nmean, K));
%		plot1(pT, N, Nmean);

		% range allowed for application (upper bounded)
		% NOTE: +3 compensates for stuttering startup
		% (special initiator behavior, slot grid must be established...)
		K = min(K, 3 + 2 * N);
		pT(K + 1 : end) = [];

		p = zeros(N, length(pT));
		for k = 1 : length(pT)
			p(:,k) = 1 - pT(k) * (1 - pT(k)) .^ [0 : rows(p) - 1]';
		endfor
		p = cumprod(p, 2);

		s = [];
		for n = 2 : N
			k = find(p(n,:) < ptest, 1);
			if (isempty(k))
				break;
			endif
			s(end + 1) = k;
		endfor
		if (isempty(s) || (s(end) < K && length(s) < N - 1))
			s(end+1) = K;
		endif

		% compensate for stuttering startup
		s(1 : min(3, length(s))) += [3 2 1](1 : min(3, length(s)));
		if (!issorted(s))
			error("s is not strictly increasing");
		endif

		data{N} = struct();
		data{N}.Nmean = Nmean;
		data{N}.K = K;
		data{N}.p = pT(end);
		data{N}.s = s;

	endfor
	printf("\n");

	text_h = "";

	text_h = [text_h, sprintf("static const uint16_t %s = (\n", p_name)];
	for N = 2 : Nmax
		text_h = [text_h, sprintf("\t(!!(MX_NUM_NODES == %3u) * %u) +\n", N, round(data{N}.p * 65536))];
	endfor
	text_h = [text_h, sprintf("\t0);\n\nASSERT_CT_STATIC(0 != %s, MX_NUM_NODES_invalid);", p_name)];

	text_h = [text_h, sprintf("\n\nstatic const uint16_t %s_SIZE = (\n", lut_name)];
	for N = 2 : Nmax
		text_h = [text_h, sprintf("\t(!!(MX_NUM_NODES == %3u) * %u) +\n", N, length(data{N}.s))];
	endfor
	text_h = [text_h, sprintf("\t0);\n\nASSERT_CT_STATIC(0 != %s_SIZE, MX_NUM_NODES_invalid);", lut_name)];

%	text_h = [text_h, sprintf("\n\nextern const uint16_t* const %s;", lut_name)];
%	text_h = [text_h, sprintf("\n\nextern const uint16_t %s[%s_SIZE];", lut_name, lut_name)];

	text_h = [text_h, "\n"];
	for N = 2 : Nmax
		text_h = [text_h, sprintf("\nextern const uint16_t %s_%u[];",  lut_name, N)];
	endfor
	text_h = [text_h, sprintf("\n\nstatic const uint16_t* const %s = (const uint16_t*)(\n", lut_name)];
	for N = 2 : Nmax
		text_h = [text_h, sprintf("\t(!!(MX_NUM_NODES == %3u) * (uintptr_t)&%s_%u) +\n", N, lut_name, N)];
	endfor
	text_h = [text_h, sprintf("\t0);\n\nASSERT_CT_STATIC(0 != %s, MX_NUM_NODES_invalid);", lut_name)];

	text_c = "";
	text_c = [text_c, sprintf("// p_test = %f", ptest)];

	for N = 2 : Nmax
		text_c = [text_c, sprintf("\n\nconst uint16_t %s_%u[] =\n\t{ %u", lut_name, N, data{N}.s(1))];
		if (length(data{N}.s) > 1)
			text_c = [text_c, sprintf(", %u", data{N}.s(2:end))];
		endif
		text_c = [text_c, sprintf(" };\n")];
		text_c = [text_c, sprintf("\t// E[density] = %u, exit_slot_max = %u", data{N}.Nmean, data{N}.K)];
	endfor

	[f, p] = uigetfile("*.h", "Open *.h template", "mixer_discovery_template.h");
	if (!f)
		return;
	endif
	f = [p, f];
	f = fopen(f, "rt");
	fmt_h = fread(f, inf, "*char")';
	fclose(f);

	[f, p] = uigetfile("*.c", "Open *.c template", "mixer_discovery_template.c");
	if (!f)
		return;
	endif
	f = [p, f];
	f = fopen(f, "rt");
	fmt_c = fread(f, inf, "*char")';
	fclose(f);

	[f, p] = uiputfile("*.h", "Save *.h as", "mixer_discovery.h");
	if (!f)
		return;
	endif
	f = [p, f];
	f = fopen(f, "wt");
	fprintf(f, fmt_h, text_h);
	fclose(f);

	[f, p] = uiputfile("*.c", "Save *.c as", "mixer_discovery.c");
	if (!f)
		return;
	endif
	f = [p, f];
	f = fopen(f, "wt");
	fprintf(f, fmt_c, text_c);
	fclose(f);

endif
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
